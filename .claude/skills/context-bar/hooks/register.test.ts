import { expect, test } from 'claude-code/testing'
import type { SessionContextBreakdown } from 'claude-code'

import { allocate, formatTokens } from './register'

const BREAKDOWN = {
  categories: [
    { name: 'System prompt', tokens: 3000, color: 'promptBorder', isDeferred: false, kind: 'used' },
    { name: 'Messages', tokens: 47000, color: 'permission', isDeferred: false, kind: 'used' },
    { name: 'MCP tools (deferred)', tokens: 9000, color: 'inactive', isDeferred: true, kind: 'deferred' },
    { name: 'Free space', tokens: 117000, color: 'inactive', isDeferred: false, kind: 'free' },
    { name: 'Autocompact buffer', tokens: 33000, color: 'inactive', isDeferred: false, kind: 'buffer' },
  ],
  totalTokens: 50000,
  maxTokens: 200000,
  rawMaxTokens: 200000,
  autocompactSource: 'model-default',
  percentage: 25,
  gridRows: [],
  model: 'claude-opus-5-5',
  memoryFiles: [],
  mcpTools: [],
  agents: [],
  isAutoCompactEnabled: true,
  apiUsage: null,
} as unknown as SessionContextBreakdown

const RUN = {
  command: 'context-bar',
  args: '',
  origin: { kind: 'composer' },
  presentation: { isFullscreen: false, columns: 80 },
} as const

test('allocate fills the width and gives every segment a cell', async () => {
  const cells = allocate([1, 1000, 50], 40)
  expect(cells.reduce((a, c) => a + c, 0)).toBe(40)
  expect(cells[0]).toBe(1)
  expect(allocate([], 40)).toEqual([])
})

test('formatTokens abbreviates', async () => {
  expect(formatTokens(950)).toBe('950')
  expect(formatTokens(3200)).toBe('3.2k')
  expect(formatTokens(200000)).toBe('200k')
  expect(formatTokens(1000000)).toBe('1.0M')
})

test('the bar draws above the prompt and /context-bar toggles it', async ($, on) => {
  on('session.usage', async () => ({
    value: {
      startedAt: 0,
      context: { window: 200000, tokens: 50000, percent: 25, breakdown: BREAKDOWN },
      rateLimits: [],
    },
  }) as never)
  // the engine's own band: nothing
  on('ui.render', async () => h('Text', null, 'engine band') as never)

  // starts shown; toggle off then on so the "on" path refreshes from usage
  expect((await $.command.run(RUN as never)).text).toBe('Context bar off.')
  expect((await $.command.run(RUN as never)).text).toBe('Context bar on.')

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({
      plugin: 'context-bar',
      surface,
      component: 'AbovePrompt',
      props: { hasSurvey: false, isWorking: false } as never,
      viewport: { columns: 82, rows: 40 } as never,
    })
    expect(await ui.find({ type: 'Text', text: /50k \/ 200k \(25%\)/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Messages 47k/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /deferred/ })).toBeUndefined()
    await ui.unmount()
  }

  expect((await $.command.run(RUN as never)).text).toBe('Context bar off.')
  const hidden = await $.ui.mount({
    plugin: 'context-bar',
    surface: 'terminal',
    component: 'AbovePrompt',
    props: { hasSurvey: false, isWorking: false } as never,
  })
  expect(await hidden.find({ type: 'Text', text: /Context/ })).toBeUndefined()
  expect(await hidden.find({ type: 'Text', text: 'engine band' })).toBeDefined()
})
