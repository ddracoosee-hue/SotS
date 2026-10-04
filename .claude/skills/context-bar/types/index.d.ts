export type BarSegment = {
  name: string
  tokens: number
  color: string
  kind: 'used' | 'free' | 'buffer'
}

export type BarSnapshot = {
  segments: BarSegment[]
  totalTokens: number
  maxTokens: number
  percentage: number
}

declare module 'claude-code' {
  interface PluginState {
    'context-bar': { isShown: boolean; snapshot: BarSnapshot | null }
  }
}
