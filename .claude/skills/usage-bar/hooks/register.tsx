import { atom, read, update } from 'claude-code'
import type { Hook, Register, SessionRateLimit } from 'claude-code'

import type { LimitWindow, TokenTotals } from '../types'

const ZERO: TokenTotals = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, turns: 0 }

const isShown = atom({ plugin: 'usage-bar', key: 'isShown' } as const, true)
const totals = atom({ plugin: 'usage-bar', key: 'totals' } as const, ZERO)
const limits = atom({ plugin: 'usage-bar', key: 'limits' } as const, [])
const costUsd = atom({ plugin: 'usage-bar', key: 'costUsd' } as const, null)

/** One color per token category, as /context gives one per context category. */
export const TOKEN_CATEGORIES = [
  { key: 'input', name: 'Input', color: 'suggestion' },
  { key: 'output', name: 'Output', color: 'claude' },
  { key: 'cacheRead', name: 'Cache read', color: 'success' },
  { key: 'cacheWrite', name: 'Cache write', color: 'warning' },
] as const

/** One color per usage-limit window. */
const LIMIT_COLORS: Record<string, string> = {
  five_hour: 'permission',
  seven_day: 'planMode',
  spend_limit: 'autoAccept',
}

const LIMIT_LABELS: Record<string, string> = {
  five_hour: 'Session (5h)',
  seven_day: 'Week (7d)',
  spend_limit: 'Spend',
}

/** Splits `width` cells across values by share; every nonzero value gets at least one. */
export function allocate(values: number[], width: number): number[] {
  const sum = values.reduce((a, t) => a + t, 0)
  if (sum <= 0 || values.length === 0) return values.map(() => 0)
  const exact = values.map(t => (t / sum) * width)
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
    if ((cells[i] ?? 0) > 0 || (values[i] ?? 0) <= 0) continue
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

export function formatResetIn(resetsAt: string | undefined, now: number): string {
  if (!resetsAt) return ''
  const ms = Date.parse(resetsAt) - now
  if (!Number.isFinite(ms) || ms <= 0) return ''
  const mins = Math.round(ms / 60_000)
  if (mins < 60) return `resets in ${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 48) return `resets in ${hours}h ${mins % 60}m`
  return `resets in ${Math.round(hours / 24)}d`
}

function toWindows(list: readonly SessionRateLimit[]): LimitWindow[] {
  return list.map(l => ({ kind: l.kind, percentUsed: l.percentUsed, resetsAt: l.resetsAt }))
}

async function refreshLimits($: Parameters<Hook<'session.start'>>[0]) {
  try {
    const usage = await $.session.usage()
    await update($, limits, () => toWindows(usage.rateLimits))
    await update($, costUsd, () => usage.cost?.usd ?? null)
  } catch {
    // no session bound yet; the next measurement fills it
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'usage-bar',
      description: 'Toggle the session token and usage-limit bar above the prompt',
    })
    const ran = await next(e)
    void refreshLimits($)
    return ran
  })

  on('session.measure', async ($, e, next) => {
    await update($, limits, () => toWindows(e.rateLimits))
    await update($, costUsd, () => e.cost?.usd ?? null)
    return next(e)
  })

  // every turn's tokens, the main loop's and each subagent's
  on('turn.complete', async ($, e, next) => {
    const u = e.usage
    if (u) {
      await update($, totals, t => ({
        input: t.input + u.input_tokens,
        output: t.output + u.output_tokens,
        cacheRead: t.cacheRead + u.cache_read_input_tokens,
        cacheWrite: t.cacheWrite + u.cache_creation_input_tokens,
        turns: t.turns + 1,
      }))
    }
    return next(e)
  })

  on('command.run', { command: 'usage-bar' }, async $ => {
    const shown = !(await read($, isShown))
    await update($, isShown, () => shown)
    if (shown) await refreshLimits($)
    return { text: shown ? 'Usage bar on.' : 'Usage bar off.' }
  })

  // drawn beneath whatever the plugins under this one draw (the context bar)
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey || !(await read($, isShown))) return next(e)
    const t = await read($, totals)
    const windows = await read($, limits)
    const usd = await read($, costUsd)
    if (t.turns === 0 && windows.length === 0) return next(e)

    const below = await next(e)
    const { Box, Text } = $.ui.resolve(e)
    const columns = e.viewport?.columns ?? 80
    const width = Math.max(10, columns - 2)
    const values = TOKEN_CATEGORIES.map(c => t[c.key])
    const sum = values.reduce((a, v) => a + v, 0)
    const cells = allocate(values, width)
    const now = await $.clock.now()
    const meterWidth = Math.max(5, Math.min(20, Math.floor(columns / 4)))

    return (
      <Box flexDirection="column">
        {below}
        <Text>
          <Text bold>Usage </Text>
          <Text dimColor>
            {formatTokens(sum)} tokens · {t.turns} turns
            {usd === null ? '' : ` · $${usd.toFixed(2)}`}
          </Text>
        </Text>
        {sum > 0 && (
          <Text wrap="truncate">
            {TOKEN_CATEGORIES.map((c, i) => (
              <Text color={c.color}>{'█'.repeat(cells[i] ?? 0)}</Text>
            ))}
          </Text>
        )}
        {sum > 0 && (
          <Text wrap="wrap">
            {TOKEN_CATEGORIES.map((c, i) => (
              <Text>
                <Text color={c.color}>█</Text>
                <Text dimColor>
                  {' '}
                  {c.name} {formatTokens(values[i] ?? 0)}
                  {'  '}
                </Text>
              </Text>
            ))}
          </Text>
        )}
        {windows.map(w => {
          const filled = Math.min(meterWidth, Math.round((w.percentUsed / 100) * meterWidth))
          const reset = formatResetIn(w.resetsAt, now)
          return (
            <Text wrap="truncate">
              <Text dimColor>{(LIMIT_LABELS[w.kind] ?? w.kind).padEnd(13)}</Text>
              <Text color={LIMIT_COLORS[w.kind] ?? 'suggestion'}>{'█'.repeat(filled)}</Text>
              <Text dimColor>{'░'.repeat(meterWidth - filled)}</Text>
              <Text> {w.percentUsed}%</Text>
              <Text dimColor>{reset ? ` · ${reset}` : ''}</Text>
            </Text>
          )
        })}
      </Box>
    )
  })
}
