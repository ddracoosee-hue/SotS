export type Kind = 'plan' | 'research' | 'build' | 'test' | 'fix' | 'docs' | 'ship'
export type Status = 'done' | 'active' | 'todo'

export type Task = { id: string; title: string; kind: Kind; status: Status }

export type Roadmap = {
  project: string
  goal: string
  tasks: Task[]
  analyzedAt: number
}

export type Analysis = {
  state: 'idle' | 'running' | 'error'
  message?: string
  /** when the folder last changed in a way the watcher saw */
  changedAt?: number
}

declare module 'claude-code' {
  interface PluginState {
    'project-dashboard': {
      roadmap: Roadmap | null
      analysis: Analysis
      session: Task[]
      /** task key -> when its cross-off animation started */
      flashes: Record<string, number>
      /** the animation clock: the time of the last frame */
      tick: number
      isWorking: boolean
    }
  }
}
