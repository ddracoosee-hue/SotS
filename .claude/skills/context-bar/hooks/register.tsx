import { atom, read, update } from 'claude-code'
import type { Hook, Register, SessionContextBreakdown } from 'claude-code'

import type { BarSegment, BarSnapshot } from '../types'

const isShown = atom({ plugin: 'context-bar', key: 'isShown' } as const, true)
const snapshot = atom({ plugin: 'context-bar', key: 'snapshot' } as const, null)

const GLYPH: Record<BarSegment['kind'], string> = { used: '█', buffer: '▒', free: '░' }

export function toSnapshot(b: SessionContextBreakdown): BarSnapshot {
  const segments: BarSegment[] = []
  for (const c of b.categories) {
    if (c.kind === 'deferred' || c.tokens <= 0) continue
    segments.push({ name: c.name, tokens: c.tokens, color: c.color, kind: c.kind })
  }
  return {
    segments,
    totalTokens: b.totalTokens,
    maxTokens: b.rawMaxTokens,
    percentage: b.percentage,
  }
}

/** Splits `width` cells across segments by token share; every segment gets at least one. */
export function allocate(tokens: number[], width: number): number[] {
  const sum = tokens.reduce((a, t) => a + t, 0)
  if (sum <= 0 || tokens.length === 0) return tokens.map(() => 0)
  const exact = tokens.map(t => (t / sum) * width)
  const cells = exact.map(Math.floor)
  let left = width - cells.reduce((a, c) => a + c, 0)
  const byRemainder = exact
    .map((x, i) => ({ i, r: x - Math.floor(x) }))
    .sort((a, b) => b.r - a.r)
  for (const { i } of byRemainder) {
    if (left <= 0) break
    cells[i] = (cells[i] ?? 0) + 1
    left -= 1
  }
  for (let i = 0; i < cells.length; i++) {
    if ((cells[i] ?? 0) > 0 || (tokens[i] ?? 0) <= 0) continue
    const most = Math.max(...cells)
    if (most <= 1) break
    const donor = cells.indexOf(most)
    cells[donor] = most - 1
    cells[i] = 1
  }
  return cells
}

export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`
  return `${n}`
}

async function refresh($: Parameters<Hook<'session.start'>>[0]) {
  if (!(await read($, isShown))) return
  try {
    const usage = await $.session.usage({ breakdown: 'summary' })
    const b = usage.context.breakdown
    if (b) await update($, snapshot, () => toSnapshot(b))
  } catch {
    // no session bound yet; the next measurement fills it
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'context-bar',
      description: 'Toggle the context window bar above the prompt',
    })
    const ran = await next(e)
    void refresh($)
    return ran
  })

  on('session.measure', async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  on('command.run', { command: 'context-bar' }, async $ => {
    const shown = !(await read($, isShown))
    await update($, isShown, () => shown)
    if (shown) await refresh($)
    return { text: shown ? 'Context bar on.' : 'Context bar off.' }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey || !(await read($, isShown))) return next(e)
    const snap = await read($, snapshot)
    if (!snap || snap.segments.length === 0) return next(e)

    const { Box, Text } = $.ui.resolve(e)
    const width = Math.max(10, (e.viewport?.columns ?? 80) - 2)
    const cells = allocate(snap.segments.map(s => s.tokens), width)

    return (
      <Box flexDirection="column">
        <Text>
          <Text bold>Context </Text>
          <Text dimColor>
            {formatTokens(snap.totalTokens)} / {formatTokens(snap.maxTokens)} ({snap.percentage}%)
          </Text>
        </Text>
        <Text wrap="truncate">
          {snap.segments.map((s, i) => (
            <Text color={s.color} dimColor={s.kind === 'free'}>
              {GLYPH[s.kind].repeat(cells[i] ?? 0)}
            </Text>
          ))}
        </Text>
        <Text wrap="wrap">
          {snap.segments.map(s => (
            <Text>
              <Text color={s.color}>{GLYPH[s.kind]}</Text>
              <Text dimColor>
                {' '}
                {s.name} {formatTokens(s.tokens)}
                {'  '}
              </Text>
            </Text>
          ))}
        </Text>
      </Box>
    )
  })
}
