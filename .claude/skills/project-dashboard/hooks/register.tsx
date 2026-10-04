import { atom, read, update } from 'claude-code'
import type { Hook, Register, Timer } from 'claude-code'

import type { Analysis, Kind, Roadmap, Status, Task } from '../types'

type Dollar = Parameters<Hook<'session.start'>>[0]

const PANE = 'project-dashboard'
const MODEL = 'sonnet'
const POLL_MS = 10_000
const SETTLE_MS = 20_000
const MIN_GAP_MS = 90_000
const FRAME_MS = 80
const STRIKE_MS = 700
const FLASH_MS = 1_500
const PULSE_MS = 600

const roadmap = atom({ plugin: 'project-dashboard', key: 'roadmap' } as const, null)
const analysis = atom({ plugin: 'project-dashboard', key: 'analysis' } as const, { state: 'idle' })
const session = atom({ plugin: 'project-dashboard', key: 'session' } as const, [])
const flashes = atom({ plugin: 'project-dashboard', key: 'flashes' } as const, {})
const tick = atom({ plugin: 'project-dashboard', key: 'tick' } as const, 0)
const isWorking = atom({ plugin: 'project-dashboard', key: 'isWorking' } as const, false)

/** One color per kind of step. */
export const KINDS: { kind: Kind; label: string; color: string }[] = [
  { kind: 'plan', label: 'Plan', color: 'planMode' },
  { kind: 'research', label: 'Research', color: 'suggestion' },
  { kind: 'build', label: 'Build', color: 'claude' },
  { kind: 'test', label: 'Test', color: 'success' },
  { kind: 'fix', label: 'Fix', color: 'error' },
  { kind: 'docs', label: 'Docs', color: 'permission' },
  { kind: 'ship', label: 'Ship', color: 'warning' },
]
const KIND_SET = new Set<string>(KINDS.map(k => k.kind))
const colorOf = (kind: Kind) => KINDS.find(k => k.kind === kind)?.color ?? 'claude'

// ---------------------------------------------------------------------------
// Reading the project

const DOC_NAME = /(plan|todo|roadmap|next|tasks|milestone|changelog|status|handoff|claude\.md|readme)/i
const DOC_DIRS = ['docs', 'doc', 'plans', 'blueprint', 'coord', '.claude/plans']
const MAX_DOC_CHARS = 12_000
const MAX_TOTAL_CHARS = 60_000

function join(dir: string, name: string): string {
  return /[\\/]$/.test(dir) ? `${dir}${name}` : `${dir}/${name}`
}

export function baseName(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() ?? path
}

/** The planning documents the dashboard reads and watches, newest first. */
async function findDocs($: Dollar, cwd: string): Promise<{ path: string; mtimeMs: number }[]> {
  const found: { path: string; mtimeMs: number }[] = []
  const scan = async (dir: string) => {
    try {
      for (const entry of await $.fs.list(dir)) {
        if (entry.kind === 'file' && /\.(md|txt)$/i.test(entry.name) && DOC_NAME.test(entry.name)) {
          found.push({ path: join(dir, entry.name), mtimeMs: entry.mtimeMs })
        }
      }
    } catch {
      // the folder is not there
    }
  }
  await scan(cwd)
  for (const sub of DOC_DIRS) await scan(join(cwd, sub))
  return found.sort((a, b) => b.mtimeMs - a.mtimeMs).slice(0, 12)
}

async function git($: Dollar, cwd: string, args: string[]): Promise<string> {
  try {
    const r = await $.process.run(['git', ...args], { cwd, timeoutMs: 15_000 })
    return r.exitCode === 0 ? r.stdout : ''
  } catch {
    return ''
  }
}

/** What the watcher compares: doc times, the commit, and the working tree. */
async function fingerprint($: Dollar, cwd: string): Promise<string> {
  const docs = await findDocs($, cwd)
  const head = (await git($, cwd, ['rev-parse', 'HEAD'])).trim()
  const status = await git($, cwd, ['status', '--porcelain'])
  return [docs.map(d => `${d.path}@${d.mtimeMs}`).join('|'), head, hash(status)].join('#')
}

export function hash(text: string): string {
  let h = 5381
  for (let i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0
  return `${text.length}:${h >>> 0}`
}

async function gatherContext($: Dollar, cwd: string): Promise<string> {
  const parts: string[] = []
  let total = 0
  const add = (title: string, body: string) => {
    if (!body.trim() || total >= MAX_TOTAL_CHARS) return
    const text = body.slice(0, Math.min(MAX_DOC_CHARS, MAX_TOTAL_CHARS - total))
    total += text.length
    parts.push(`<<< ${title} >>>\n${text}`)
  }
  try {
    const names = (await $.fs.list(cwd))
      .filter(e => !e.name.startsWith('.') || e.name === '.claude')
      .map(e => (e.kind === 'dir' ? `${e.name}/` : e.name))
    add('top-level entries', names.join('\n'))
  } catch {
    // unreadable folder; the docs and git may still say enough
  }
  for (const doc of await findDocs($, cwd)) {
    try {
      add(doc.path.slice(cwd.length).replace(/^[\\/]/, ''), await $.fs.read(doc.path))
    } catch {
      // vanished between list and read
    }
  }
  add('git log (newest first)', await git($, cwd, ['log', '--oneline', '-30']))
  add('git status', (await git($, cwd, ['status', '--short'])).split('\n').slice(0, 60).join('\n'))
  return parts.join('\n\n')
}

// ---------------------------------------------------------------------------
// Asking Claude for the chain

const SYSTEM = `You read a software project's planning documents, file list and git history and work out its chain of tasks: the ordered steps from where it started to where it is going.
Answer with one JSON object and nothing else:
{"project":"<short name>","goal":"<one line, under 80 chars>","tasks":[{"id":"<kebab-case, stable>","title":"<under 60 chars, imperative>","kind":"plan|research|build|test|fix|docs|ship","status":"done|active|todo"}]}
Rules:
- 8 to 30 tasks, in the order they happen; finished work first.
- "done" only with evidence (a commit, a checked box, a doc saying it is complete). "active" for what is in progress now: at most two. Everything after is "todo".
- Prefer the project's own plan and checklist wording and numbering when it has one.
- When a previous chain is given, keep its ids and titles for the same tasks, so the dashboard can tell what moved.`

export function parseRoadmap(text: string, now: number, fallbackName: string): Roadmap | null {
  const start = text.indexOf('{')
  const end = text.lastIndexOf('}')
  if (start < 0 || end <= start) return null
  let raw: unknown
  try {
    raw = JSON.parse(text.slice(start, end + 1))
  } catch {
    return null
  }
  if (!raw || typeof raw !== 'object') return null
  const obj = raw as { project?: unknown; goal?: unknown; tasks?: unknown }
  if (!Array.isArray(obj.tasks)) return null
  const seen = new Set<string>()
  const tasks: Task[] = []
  for (const t of obj.tasks as unknown[]) {
    if (!t || typeof t !== 'object') continue
    const { id, title, kind, status } = t as Record<string, unknown>
    if (typeof title !== 'string' || !title.trim()) continue
    let key = typeof id === 'string' && id.trim() ? id.trim() : title.toLowerCase().replace(/\W+/g, '-')
    while (seen.has(key)) key += '-'
    seen.add(key)
    tasks.push({
      id: key,
      title: title.trim().slice(0, 80),
      kind: typeof kind === 'string' && KIND_SET.has(kind) ? (kind as Kind) : 'build',
      status: status === 'done' || status === 'active' ? status : 'todo',
    })
  }
  if (tasks.length === 0) return null
  return {
    project: typeof obj.project === 'string' && obj.project.trim() ? obj.project.trim() : fallbackName,
    goal: typeof obj.goal === 'string' ? obj.goal.trim().slice(0, 120) : '',
    tasks,
    analyzedAt: now,
  }
}

/** Keys of tasks that are done now and were not before: the ones to cross off. */
export function newlyDone(before: Task[], after: Task[], prefix: string): string[] {
  const was = new Map(before.map(t => [t.id, t.status]))
  return after
    .filter(t => t.status === 'done' && was.has(t.id) && was.get(t.id) !== 'done')
    .map(t => `${prefix}${t.id}`)
}

let isAnalyzing = false
let lastAnalysisAt = 0

async function analyze($: Dollar, cwd: string) {
  if (isAnalyzing) return
  isAnalyzing = true
  lastAnalysisAt = await $.clock.now()
  await update($, analysis, (a): Analysis => ({ ...a, state: 'running', message: undefined }))
  try {
    const previous = await read($, roadmap)
    const context = await gatherContext($, cwd)
    const prior = previous
      ? `\n\nPrevious chain:\n${JSON.stringify({ project: previous.project, goal: previous.goal, tasks: previous.tasks })}`
      : ''
    const r = await $.model.complete({
      model: MODEL,
      system: SYSTEM,
      prompt: `Project folder: ${cwd}\n\n${context}${prior}`,
      maxTokens: 4000,
    })
    if (!r.isAnswered) {
      await update($, analysis, (a): Analysis => ({ ...a, state: 'error', message: `model: ${r.reason}` }))
      return
    }
    const next = parseRoadmap(r.text, await $.clock.now(), baseName(cwd))
    if (!next) {
      await update($, analysis, (a): Analysis => ({ ...a, state: 'error', message: 'could not read the chain' }))
      return
    }
    await crossOff($, newlyDone(previous?.tasks ?? [], next.tasks, 'r:'))
    await update($, roadmap, () => next)
    await update($, analysis, (a): Analysis => ({ ...a, state: 'idle', message: undefined }))
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    await update($, analysis, (a): Analysis => ({ ...a, state: 'error', message: message.slice(0, 80) }))
  } finally {
    isAnalyzing = false
  }
}

// ---------------------------------------------------------------------------
// Animation

let frames: Timer | null = null
let pulse: Timer | null = null

async function crossOff($: Dollar, keys: string[]) {
  if (keys.length === 0) return
  const now = await $.clock.now()
  await update($, flashes, f => {
    const out = { ...f }
    for (const key of keys) out[key] = now
    return out
  })
  startFrames($)
}

function startFrames($: Dollar) {
  if (frames) return
  frames = $.clock.every(FRAME_MS, () => {
    void (async () => {
      const now = await $.clock.now()
      const live = await update($, flashes, f => {
        const out: Record<string, number> = {}
        for (const [k, at] of Object.entries(f)) if (now - at < FLASH_MS) out[k] = at
        return out
      })
      await update($, tick, () => now)
      if (Object.keys(live).length === 0) {
        frames?.cancel()
        frames = null
      }
    })()
  })
}

function startPulse($: Dollar) {
  if (pulse) return
  pulse = $.clock.every(PULSE_MS, () => {
    void (async () => {
      const now = await $.clock.now()
      await update($, tick, () => now)
    })()
  })
}

function stopPulse() {
  pulse?.cancel()
  pulse = null
}

// ---------------------------------------------------------------------------
// Watching the folder

let watcher: Timer | null = null
let settle: Timer | null = null
let lastPrint = ''

async function startWatching($: Dollar, cwd: string) {
  watcher?.cancel()
  lastPrint = await fingerprint($, cwd)
  watcher = $.clock.every(POLL_MS, () => {
    void (async () => {
      const print = await fingerprint($, cwd)
      if (print === lastPrint) return
      lastPrint = print
      const now = await $.clock.now()
      await update($, analysis, (a): Analysis => ({ ...a, changedAt: now }))
      // wait for the edits to settle, and keep model calls apart
      settle?.cancel()
      const wait = Math.max(SETTLE_MS, lastAnalysisAt + MIN_GAP_MS - now)
      settle = $.clock.after(wait, () => void analyze($, cwd))
    })()
  })
}

// ---------------------------------------------------------------------------
// Claude's own task list this session (TaskCreate / TaskUpdate / TodoWrite)

function todoStatus(s: string): Status {
  return s === 'completed' ? 'done' : s === 'in_progress' ? 'active' : 'todo'
}

export function kindFromTitle(title: string): Kind {
  const t = title.toLowerCase()
  if (/\b(test|verify|check|validate|assert)/.test(t)) return 'test'
  if (/\b(fix|bug|repair|debug)/.test(t)) return 'fix'
  if (/\b(doc|readme|write up|explain)/.test(t)) return 'docs'
  if (/\b(push|deploy|release|ship|merge|publish|commit)/.test(t)) return 'ship'
  if (/\b(plan|design|outline|decide)/.test(t)) return 'plan'
  if (/\b(read|research|investigate|explore|find|look)/.test(t)) return 'research'
  return 'build'
}

async function setSession($: Dollar, next: Task[]) {
  const before = await read($, session)
  await crossOff($, newlyDone(before, next, 's:'))
  await update($, session, () => next)
}

// ---------------------------------------------------------------------------
// Drawing

export function windowAround(tasks: Task[], room: number): Task[] {
  if (tasks.length <= room) return tasks
  const firstOpen = tasks.findIndex(t => t.status !== 'done')
  const anchor = firstOpen < 0 ? tasks.length - 1 : firstOpen
  const start = Math.max(0, Math.min(anchor - 2, tasks.length - room))
  return tasks.slice(start, start + room)
}

export function bar(done: number, total: number, width: number): [string, string] {
  const filled = total === 0 ? 0 : Math.round((done / total) * width)
  return ['█'.repeat(filled), '░'.repeat(width - filled)]
}

export function ago(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s}s ago`
  const m = Math.round(s / 60)
  return m < 60 ? `${m}m ago` : `${Math.round(m / 60)}h ago`
}

export const register: Register = on => {
  let cwd = ''

  on('session.start', async ($, e, next) => {
    cwd = e.cwd
    await $.command.register({
      name: 'dashboard',
      description: 'Open the project dashboard (refresh: re-read the project, close: hide it)',
    })
    const ran = await next(e)
    if (e.isInteractive) void $.ui.open({ id: PANE, title: 'Project' })
    void startWatching($, cwd)
    if (!(await read($, roadmap))) void analyze($, cwd)
    return ran
  })

  on('command.run', { command: 'dashboard' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    if (!cwd) cwd = await $.session.cwd()
    if (arg === 'close') {
      await $.ui.close({ id: PANE })
      return { text: 'Dashboard closed.' }
    }
    const opened = await $.ui.open({ id: PANE, title: 'Project' })
    if (arg === 'refresh' || !(await read($, roadmap))) void analyze($, cwd)
    if (!opened.isPlaced) return { text: 'Dashboard is open but the terminal is too narrow to show it.' }
    return { text: arg === 'refresh' ? 'Re-reading the project.' : 'Dashboard open.' }
  })

  on('prompt.submit', async ($, e, next) => {
    await update($, isWorking, () => true)
    startPulse($)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (!e.agentId) {
      await update($, isWorking, () => false)
      stopPulse()
    }
    return next(e)
  })

  on('tool.call', { tool: 'TodoWrite' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError) {
      await setSession(
        $,
        e.todos.map(t => ({
          id: t.content,
          title: t.content,
          kind: kindFromTitle(t.content),
          status: todoStatus(t.status),
        })),
      )
    }
    return ran
  })

  on('tool.call', { tool: 'TaskCreate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError) {
      const id = ran.result.task.id
      const list = await read($, session)
      await setSession($, [
        ...list.filter(t => t.id !== id),
        { id, title: e.subject, kind: kindFromTitle(e.subject), status: 'todo' },
      ])
    }
    return ran
  })

  on('tool.call', { tool: 'TaskUpdate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError) {
      const list = await read($, session)
      const nextList =
        e.status === 'deleted'
          ? list.filter(t => t.id !== e.taskId)
          : list.map(t =>
              t.id !== e.taskId
                ? t
                : {
                    ...t,
                    title: e.subject ?? t.title,
                    status: e.status ? todoStatus(e.status) : t.status,
                  },
            )
      await setSession($, nextList)
    }
    return ran
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const map = await read($, roadmap)
    const state = await read($, analysis)
    const live = await read($, session)
    const flash = await read($, flashes)
    const working = await read($, isWorking)
    const now = Math.max(await read($, tick), await $.clock.now())
    const width = Math.max(20, e.props.bodyColumns)
    const pulseOn = working && Math.floor(now / PULSE_MS) % 2 === 0

    const row = (task: Task, key: string, isNow: boolean) => {
      const at = flash[key]
      const age = at === undefined ? Infinity : now - at
      const title = task.title.slice(0, width - 4)
      if (task.status === 'done' && age < FLASH_MS) {
        // the strike sweeps across the title, then the tick pops
        const struck = Math.min(title.length, Math.ceil((age / STRIKE_MS) * title.length))
        const isPopped = age >= STRIKE_MS
        return (
          <Text wrap="truncate">
            <Text color="success" bold={isPopped}>{isPopped ? '✔ ' : '· '}</Text>
            <Text color="success" strikethrough>{title.slice(0, struck)}</Text>
            <Text>{title.slice(struck)}</Text>
          </Text>
        )
      }
      if (task.status === 'done') {
        return (
          <Text wrap="truncate" dimColor>
            <Text color="success">✓ </Text>
            <Text strikethrough>{title}</Text>
          </Text>
        )
      }
      if (task.status === 'active' || isNow) {
        return (
          <Text wrap="truncate">
            <Text color={colorOf(task.kind)} bold>{pulseOn ? '▹ ' : '▸ '}</Text>
            <Text bold>{title}</Text>
          </Text>
        )
      }
      return (
        <Text wrap="truncate">
          <Text color={colorOf(task.kind)}>○ </Text>
          <Text dimColor>{title}</Text>
        </Text>
      )
    }

    const status =
      state.state === 'running'
        ? 'reading the project…'
        : state.state === 'error'
          ? `error: ${state.message ?? 'unknown'}`
          : map
            ? `updated ${ago(now - map.analyzedAt)}`
            : 'waiting for the first read'

    if (!map) {
      return (
        <Box flexDirection="column">
          <Text bold>Project dashboard</Text>
          <Text dimColor>{status}</Text>
          {live.length > 0 && <Text bold>This session</Text>}
          {live.map(t => row(t, `s:${t.id}`, false))}
          <Button key="refresh" label="Refresh" onPress={() => void analyze($, cwd)} />
        </Box>
      )
    }

    const tasks = map.tasks
    const done = tasks.filter(t => t.status === 'done').length
    const current = tasks.find(t => t.status === 'active') ?? tasks.find(t => t.status === 'todo')
    const upNext = tasks.filter(t => t.status !== 'done' && t !== current).slice(0, 1)[0]
    const [fill, rest] = bar(done, tasks.length, Math.max(6, Math.min(24, width - 18)))
    const pct = tasks.length === 0 ? 0 : Math.round((done / tasks.length) * 100)
    const lanes = KINDS.map(k => ({
      ...k,
      total: tasks.filter(t => t.kind === k.kind).length,
      done: tasks.filter(t => t.kind === k.kind && t.status === 'done').length,
    })).filter(l => l.total > 0)
    const room = Math.max(6, (e.viewport?.rows ?? 30) - 14 - lanes.length - Math.min(live.length, 6))

    return (
      <Box flexDirection="column">
        <Text wrap="truncate">
          <Text bold color="claude">◆ {map.project}</Text>
          <Text dimColor> · {done}/{tasks.length} done</Text>
        </Text>
        {map.goal !== '' && (
          <Text wrap="truncate" dimColor>
            {map.goal}
          </Text>
        )}
        <Text wrap="truncate">
          <Text color="success">{fill}</Text>
          <Text dimColor>{rest}</Text>
          <Text> {pct}%</Text>
        </Text>
        <Text> </Text>
        {current && (
          <Text wrap="truncate">
            <Text bold color={colorOf(current.kind)}>{pulseOn ? 'NOW ▹ ' : 'NOW ▸ '}</Text>
            <Text bold>{current.title}</Text>
          </Text>
        )}
        {upNext && (
          <Text wrap="truncate">
            <Text dimColor>NEXT  </Text>
            <Text>{upNext.title}</Text>
          </Text>
        )}
        <Text> </Text>
        <Text bold>Steps by kind</Text>
        {lanes.map(l => {
          const [f, r] = bar(l.done, l.total, Math.max(4, Math.min(12, width - 18)))
          return (
            <Text wrap="truncate">
              <Text color={l.color}>{'● '}{l.label.padEnd(9)}</Text>
              <Text color={l.color}>{f}</Text>
              <Text dimColor>{r}</Text>
              <Text dimColor> {l.done}/{l.total}</Text>
            </Text>
          )
        })}
        <Text> </Text>
        <Text bold>Chain</Text>
        {windowAround(tasks, room).map(t => row(t, `r:${t.id}`, t === current))}
        {live.length > 0 && <Text> </Text>}
        {live.length > 0 && <Text bold>This session</Text>}
        {windowAround(live, 6).map(t => row(t, `s:${t.id}`, false))}
        <Text> </Text>
        <Box flexDirection="row">
          <Text dimColor>
            {status}
            {state.changedAt && state.changedAt > map.analyzedAt && state.state !== 'running'
              ? ' · changes seen'
              : ''}{' '}
          </Text>
          <Button key="refresh" label="Refresh" onPress={() => void analyze($, cwd)} />
        </Box>
      </Box>
    )
  })
}
