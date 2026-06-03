import { defineStore } from 'pinia'
import type { AgentName, CellOutput, LogEntry, TaskSnapshot, WSMessage } from '../types/ws'

type TaskStatus = 'pending' | 'running' | 'complete' | 'error'

function eventKey(message: WSMessage): string {
  return `${message.timestamp}:${message.type}:${message.agent}:${message.content}`
}

function streamKey(message: WSMessage): string {
  const section = message.metadata?.section
  const subtask = message.metadata?.subtask_index
  return `${message.agent}:${section ?? ''}:${subtask ?? ''}`
}

export const useTaskStore = defineStore('task', {
  state: () => ({
    status: 'pending' as TaskStatus,
    messages: [] as LogEntry[],
    latestCode: '',
    latestOutput: '',
    outputImages: [] as CellOutput[],
    paperMarkdown: '',
    activeAgents: {} as Partial<Record<AgentName, boolean>>,
    currentSubtask: 0,
    totalSubtasks: 0,
    error: '',
    seen: new Set<string>(),
  }),
  actions: {
    reset() {
      this.status = 'pending'
      this.messages = []
      this.latestCode = ''
      this.latestOutput = ''
      this.outputImages = []
      this.paperMarkdown = ''
      this.activeAgents = {}
      this.currentSubtask = 0
      this.totalSubtasks = 0
      this.error = ''
      this.seen = new Set<string>()
    },
    applySnapshot(snapshot: TaskSnapshot) {
      this.status = snapshot.task.status
      this.paperMarkdown = snapshot.task.paper_markdown || ''
      this.error = snapshot.task.error || ''
      snapshot.messages.forEach((message) => this.handleMessage(message))
    },
    handleMessage(message: WSMessage) {
      if (message.type === 'heartbeat') return
      const key = eventKey(message)
      if (this.seen.has(key)) return
      this.seen.add(key)

      const metadata = message.metadata || {}
      const subtaskIndex = Number(metadata.subtask_index || 0)
      if (subtaskIndex > 0) this.currentSubtask = subtaskIndex
      const subtaskCount = Number(metadata.subtask_count || 0)
      if (subtaskCount > 0) this.totalSubtasks = subtaskCount

      if (message.type === 'agent_start') {
        this.status = this.status === 'pending' ? 'running' : this.status
        this.activeAgents[message.agent] = true
        this.messages.push({
          id: key,
          agent: message.agent,
          content: message.content,
          timestamp: message.timestamp,
          streaming: true,
          streamKey: streamKey(message),
          metadata,
        })
        return
      }

      if (message.type === 'agent_stream') {
        if (message.agent === 'writer') {
          this.paperMarkdown += message.content
        }
        const keyForStream = streamKey(message)
        const last = [...this.messages]
          .reverse()
          .find((entry) => entry.streaming && entry.streamKey === keyForStream)
        if (last) {
          last.content += message.content
        } else {
          this.messages.push({
            id: key,
            agent: message.agent,
            content: message.content,
            timestamp: message.timestamp,
            streaming: true,
            streamKey: keyForStream,
            metadata,
          })
        }
        return
      }

      if (message.type === 'agent_end') {
        this.activeAgents[message.agent] = false
        this.messages
          .filter((entry) => entry.agent === message.agent)
          .forEach((entry) => {
            entry.streaming = false
          })
        if (message.content) {
          this.messages.push({
            id: key,
            agent: message.agent,
            content: message.content,
            timestamp: message.timestamp,
            streaming: false,
            metadata,
          })
        }
        return
      }

      if (message.type === 'code_exec') {
        const outputs = (metadata.outputs || []) as CellOutput[]
        this.latestCode = String(metadata.code || '')
        this.latestOutput = [
          metadata.output ? String(metadata.output) : '',
          metadata.stderr ? String(metadata.stderr) : '',
          metadata.error ? String(metadata.error) : '',
        ]
          .filter(Boolean)
          .join('\n')
        this.outputImages = outputs.filter((item) => item.type === 'image')
        this.messages.push({
          id: key,
          agent: message.agent,
          content: message.content,
          timestamp: message.timestamp,
          streaming: false,
          metadata,
        })
        return
      }

      if (message.type === 'task_complete') {
        this.status = 'complete'
        this.activeAgents = {}
        this.paperMarkdown = String(metadata.paper_markdown || this.paperMarkdown)
      }

      if (message.type === 'error') {
        this.status = 'error'
        this.error = message.content
      }

      this.messages.push({
        id: key,
        agent: message.agent,
        content: message.content,
        timestamp: message.timestamp,
        streaming: false,
        metadata,
      })
    },
  },
})

