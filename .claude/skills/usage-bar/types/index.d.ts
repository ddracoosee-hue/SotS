export type TokenTotals = {
  input: number
  output: number
  cacheRead: number
  cacheWrite: number
  turns: number
}

export type LimitWindow = { kind: string; percentUsed: number; resetsAt?: string }

declare module 'claude-code' {
  interface PluginState {
    'usage-bar': {
      isShown: boolean
      totals: TokenTotals
      limits: LimitWindow[]
      costUsd: number | null
    }
  }
}
