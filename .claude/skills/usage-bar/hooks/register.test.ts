import { expect, mock, test } from 'claude-code/testing'

import { allocate, formatResetIn, formatTokens } from './register'

const RUN = {
  command: 'usage-bar',
  args: '',
  origin: { kind: 'composer' },
  presentation: { isFullscreen: false, columns: 80 },
} as const

const BAND = {
  plugin: 'usage-bar',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false } as never,
  viewport: { columns: 82, rows: 40 } as never,
} as const

function turn(input: number, output: number, cacheRead: number, cacheWrite: number) {
  return {
    reason: 'answer',
    isAborted: false,
    turnId: `t-${input}`,
    answer: 'done',
    usage: {
      input_tokens: input,
      output_tokens: output,
      cache_read_input_tokens: cacheRead,
      cache_creation_input_tokens: cacheWrite,
      model: 'claude-opus-5-5',
    },
  } as never
}

test('helpers', async () => {
  expect(allocate([1, 1000, 0, 50], 40).reduce((a, c) => a + c, 0)).toBe(40)
  expect(allocate([1, 1000, 0, 50], 40)[2]).toBe(0)
  expect(formatTokens(1_250_000)).toBe('1.3M')
  const now = Date.parse('2026-10-03T12:00:00Z')
  expect(formatResetIn('2026-10-03T14:14:00Z', now)).toBe('resets in 2h 14m')
  expect(formatResetIn('2026-10-03T12:30:00Z', now)).toBe('resets in 30m')
  expect(formatResetIn(undefined, now)).toBe('')
})

test('tokens add up across turns, limits draw, /usage-bar toggles', async ($, on) => {
  mock.clock(on, { now: Date.parse('2026-10-03T12:00:00Z') })
  on('turn.complete', async () => ({ text: 'done' }))
  on('session.measure', async () => ({ changed: [] }) as never)
  on('ui.render', async () => h('Text', null, 'engine band') as never)

  await $.turn.complete(turn(1000, 2000, 30000, 4000))
  await $.turn.complete(turn(500, 1000, 20000, 0))
  await $.session.measure({
    context: { window: 200000 },
    rateLimits: [
      { kind: 'five_hour', percentUsed: 23.5, resetsAt: '2026-10-03T14:14:00Z' },
      { kind: 'seven_day', percentUsed: 41 },
    ],
    cost: { usd: 1.5 },
    changed: ['rateLimits', 'cost'],
  } as never)

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect(await ui.find({ type: 'Text', text: /59k tokens · 2 turns · \$1\.50/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Cache read 50k/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Output 3\.0k/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Session \(5h\).*23\.5% · resets in 2h 14m/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Week \(7d\).*41%/ })).toBeDefined()
    // what the plugins beneath draw stays, above the usage rows
    expect(await ui.find({ type: 'Text', text: 'engine band' })).toBeDefined()
    await ui.unmount()
  }

  expect((await $.command.run(RUN as never)).text).toBe('Usage bar off.')
  const hidden = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await hidden.find({ type: 'Text', text: /tokens/ })).toBeUndefined()
})
