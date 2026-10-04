import { describe, expect, mock, test } from 'claude-code/testing'

import { kindFromTitle, newlyDone, parseRoadmap, windowAround } from './register'
import type { Task } from '../types'

const T0 = Date.parse('2026-10-03T12:00:00Z')
const CWD = 'C:/work/demo'

const CHAIN = {
  project: 'demo',
  goal: 'Ship the demo app',
  tasks: [
    { id: 'plan', title: 'Write the plan', kind: 'plan', status: 'done' },
    { id: 'api', title: 'Build the API', kind: 'build', status: 'active' },
    { id: 'tests', title: 'Test the API', kind: 'test', status: 'todo' },
    { id: 'release', title: 'Release v1', kind: 'ship', status: 'todo' },
  ],
}

const t = (id: string, status: Task['status']): Task => ({ id, title: id, kind: 'build', status })

describe('helpers', () => {
  test('parseRoadmap reads JSON wrapped in prose and cleans it', async () => {
    const map = parseRoadmap(`Here you go:\n${JSON.stringify(CHAIN)}\nDone.`, T0, 'x')
    expect(map?.project).toBe('demo')
    expect(map?.tasks.length).toBe(4)
    const odd = parseRoadmap('{"tasks":[{"title":"A","kind":"weird","status":"maybe"}]}', T0, 'fallback')
    expect(odd?.project).toBe('fallback')
    expect(odd?.tasks[0]).toEqual({ id: 'a', title: 'A', kind: 'build', status: 'todo' })
    expect(parseRoadmap('no json here', T0, 'x')).toBe(null)
  })

  test('newlyDone finds only fresh completions', async () => {
    const before = [t('a', 'done'), t('b', 'active'), t('c', 'todo')]
    const after = [t('a', 'done'), t('b', 'done'), t('c', 'todo'), t('d', 'done')]
    expect(newlyDone(before, after, 'r:')).toEqual(['r:b'])
  })

  test('windowAround keeps the current task in view', async () => {
    const list = Array.from({ length: 20 }, (_, i) => t(`t${i}`, i < 12 ? 'done' : 'todo'))
    const shown = windowAround(list, 6).map(x => x.id)
    expect(shown).toEqual(['t10', 't11', 't12', 't13', 't14', 't15'])
  })

  test('kindFromTitle', async () => {
    expect(kindFromTitle('Run the tests')).toBe('test')
    expect(kindFromTitle('Fix login bug')).toBe('fix')
    expect(kindFromTitle('Push to origin')).toBe('ship')
    expect(kindFromTitle('Write register.tsx')).toBe('build')
  })
})

test('the dashboard reads the project, draws the chain and animates a cross-off', async ($, on) => {
  const clock = mock.clock(on, { now: T0 })
  let modelCalls = 0
  on('session.cwd', async () => ({ value: CWD }) as never)
  on('command.register', async () => ({ value: {} }) as never)
  on('ui.open', async () => ({ value: { isPlaced: true } }) as never)
  on('fs.list', async () => ({ value: [{ name: 'PLAN.md', kind: 'file', size: 10, mtimeMs: T0, isLink: false }] }) as never)
  on('fs.read', async () => ({ value: '# Plan\n- [x] Write the plan\n- [ ] Build the API' }) as never)
  on('process.run', async () =>
    ({ value: { exitCode: 0, stdout: 'abc123 Write the plan\n', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never,
  )
  on('model.complete', async () => {
    modelCalls += 1
    return { value: { isAnswered: true, text: JSON.stringify(CHAIN), usage: {} } } as never
  })
  on('tool.call', async e => {
    const input = e as unknown as { todos: unknown[] }
    return { result: { oldTodos: [], newTodos: input.todos } } as never
  })

  const run = await $.command.run({
    command: 'dashboard',
    args: 'refresh',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: true, columns: 160 },
  } as never)
  expect(run.text).toBe('Re-reading the project.')
  await clock.advance(10)
  expect(modelCalls).toBe(1)

  const ui = await $.ui.mount({
    plugin: 'project-dashboard',
    surface: 'terminal',
    component: 'Pane',
    requestId: 'project-dashboard',
    props: { title: 'Project', isFocused: false, bodyColumns: 44, placement: 'dock' } as never,
    viewport: { columns: 160, rows: 40 } as never,
  })
  expect(await ui.find({ type: 'Text', text: /◆ demo · 1\/4 done/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /NOW . Build the API/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /NEXT  Test the API/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /● Build .*0\/1/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /● Ship .*0\/1/ })).toBeDefined()

  // Claude's own task list: one task finishes and is crossed off with a sweep
  const todo = (status: string) => ({
    tool: 'TodoWrite',
    todos: [
      { content: 'Read the plan', status, activeForm: 'Reading the plan' },
      { content: 'Run the tests', status: 'pending', activeForm: 'Running the tests' },
    ],
  })
  await $.tool.call(todo('in_progress') as never)
  expect(await ui.find({ type: 'Text', text: /This session/ })).toBeDefined()
  await $.tool.call(todo('completed') as never)

  await clock.advance(320)
  await ui.redraw()
  const midway = await ui.find({ type: 'Text', text: /^· Read the plan$/ })
  expect(midway).toBeDefined()

  await clock.advance(600)
  await ui.redraw()
  expect(await ui.find({ type: 'Text', text: /^✔ Read the plan$/ })).toBeDefined()

  await clock.advance(1_000)
  await ui.redraw()
  expect(await ui.find({ type: 'Text', text: /^✓ Read the plan$/ })).toBeDefined()
  await ui.unmount()
})
