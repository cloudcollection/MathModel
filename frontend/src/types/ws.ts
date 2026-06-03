export type AgentName = 'system' | 'planner' | 'coder' | 'analyst' | 'writer'

export type WSMessageType =
  | 'agent_start'
  | 'agent_stream'
  | 'agent_end'
  | 'code_exec'
  | 'error'
  | 'task_complete'
  | 'heartbeat'

export interface CellOutput {
  type: 'text' | 'image' | 'error'
  content: string
  mime_type: string
}

export interface WSMessage {
  type: WSMessageType
  agent: AgentName
  content: string
  metadata?: Record<string, unknown>
  timestamp: string
}

export interface LogEntry {
  id: string
  agent: AgentName
  content: string
  timestamp: string
  streaming: boolean
  streamKey?: string
  metadata?: Record<string, unknown>
}

export interface TaskSnapshot {
  task: {
    id: string
    status: 'pending' | 'running' | 'complete' | 'error'
    paper_markdown: string
    error?: string | null
  }
  messages: WSMessage[]
}

