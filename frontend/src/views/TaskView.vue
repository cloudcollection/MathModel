<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Code2, Download, FileText, TerminalSquare } from '@lucide/vue'
import AgentChat from '../components/AgentChat.vue'
import CodeViewer from '../components/CodeViewer.vue'
import PaperPreview from '../components/PaperPreview.vue'
import { apiUrl, wsUrl } from '../lib/api'
import { useTaskStore } from '../stores/task'
import type { TaskSnapshot, WSMessage } from '../types/ws'

const route = useRoute()
const store = useTaskStore()
const taskId = computed(() => String(route.params.taskId))
const activeTab = ref<'code' | 'output' | 'paper'>('code')
const reconnectAttempts = ref(0)
let socket: WebSocket | null = null
let reconnectTimer: number | null = null

const progress = computed(() => {
  if (!store.totalSubtasks) return 0
  return Math.min(100, Math.round((store.currentSubtask / store.totalSubtasks) * 100))
})

const statusClass = computed(() => {
  if (store.status === 'complete') return 'bg-emerald-500'
  if (store.status === 'error') return 'bg-red-500'
  if (store.status === 'running') return 'bg-amber-500'
  return 'bg-zinc-400'
})

async function loadSnapshot() {
  const response = await fetch(apiUrl(`/api/task/${taskId.value}`))
  if (!response.ok) throw new Error(await response.text())
  store.applySnapshot((await response.json()) as TaskSnapshot)
}

function connectSocket() {
  socket?.close()
  socket = new WebSocket(wsUrl(`/ws/task/${taskId.value}`))

  socket.onopen = () => {
    reconnectAttempts.value = 0
  }

  socket.onmessage = async (event) => {
    const message = JSON.parse(event.data) as WSMessage
    store.handleMessage(message)
    if (message.type === 'task_complete') {
      await fetchPaper()
      socket?.close()
    }
  }

  socket.onclose = () => {
    if (store.status === 'complete' || store.status === 'error') return
    if (reconnectAttempts.value >= 3) return
    reconnectAttempts.value += 1
    reconnectTimer = window.setTimeout(connectSocket, 600 * 2 ** reconnectAttempts.value)
  }
}

async function fetchPaper() {
  const response = await fetch(apiUrl(`/api/task/${taskId.value}/paper`))
  if (response.ok) {
    store.paperMarkdown = await response.text()
  }
}

function downloadPaper() {
  window.location.href = apiUrl(`/api/task/${taskId.value}/download`)
}

watch(
  () => store.latestCode,
  (value) => {
    if (value) activeTab.value = 'code'
  },
)

onMounted(async () => {
  store.reset()
  await loadSnapshot()
  connectSocket()
})

onBeforeUnmount(() => {
  socket?.close()
  if (reconnectTimer) window.clearTimeout(reconnectTimer)
})
</script>

<template>
  <main class="flex h-screen min-h-0 bg-zinc-100 text-zinc-950">
    <AgentChat class="hidden w-[42%] min-w-[420px] lg:flex" :active-agents="store.activeAgents" :messages="store.messages" />

    <section class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-14 items-center justify-between border-b border-zinc-200 bg-white px-4">
        <div class="flex min-w-0 items-center gap-3">
          <span class="h-2.5 w-2.5 rounded-full" :class="statusClass"></span>
          <div class="min-w-0">
            <h1 class="truncate text-sm font-semibold text-zinc-900">Task {{ taskId }}</h1>
            <p class="text-xs capitalize text-zinc-500">{{ store.status }}</p>
          </div>
        </div>
        <button
          class="inline-flex items-center gap-2 rounded-md bg-zinc-950 px-3 py-2 text-sm font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
          :disabled="store.status !== 'complete'"
          type="button"
          @click="downloadPaper"
        >
          <Download class="h-4 w-4" />
          Download
        </button>
      </header>

      <div class="flex min-h-0 flex-1 flex-col lg:hidden">
        <AgentChat :active-agents="store.activeAgents" :messages="store.messages" />
      </div>

      <div class="flex min-h-0 flex-1 flex-col bg-white">
        <nav class="flex h-11 border-b border-zinc-200 px-3">
          <button
            class="inline-flex items-center gap-2 border-b-2 px-3 text-sm font-semibold"
            :class="activeTab === 'code' ? 'border-emerald-600 text-zinc-950' : 'border-transparent text-zinc-500'"
            type="button"
            @click="activeTab = 'code'"
          >
            <Code2 class="h-4 w-4" />
            Code
          </button>
          <button
            class="inline-flex items-center gap-2 border-b-2 px-3 text-sm font-semibold"
            :class="activeTab === 'output' ? 'border-emerald-600 text-zinc-950' : 'border-transparent text-zinc-500'"
            type="button"
            @click="activeTab = 'output'"
          >
            <TerminalSquare class="h-4 w-4" />
            Output
          </button>
          <button
            class="inline-flex items-center gap-2 border-b-2 px-3 text-sm font-semibold"
            :class="activeTab === 'paper' ? 'border-emerald-600 text-zinc-950' : 'border-transparent text-zinc-500'"
            type="button"
            @click="activeTab = 'paper'"
          >
            <FileText class="h-4 w-4" />
            Paper
          </button>
        </nav>

        <div class="min-h-0 flex-1 overflow-hidden">
          <CodeViewer v-if="activeTab === 'code'" :code="store.latestCode" />
          <div v-else-if="activeTab === 'output'" class="h-full overflow-auto p-4">
            <pre v-if="store.latestOutput" class="rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">{{ store.latestOutput }}</pre>
            <div v-else class="flex h-full items-center justify-center text-sm text-zinc-500">No output yet</div>
            <div v-if="store.outputImages.length" class="mt-4 grid gap-4 md:grid-cols-2">
              <img
                v-for="(image, index) in store.outputImages"
                :key="index"
                class="rounded-lg border border-zinc-200"
                :src="`data:${image.mime_type};base64,${image.content}`"
                alt="Execution output"
              />
            </div>
          </div>
          <PaperPreview v-else :markdown="store.paperMarkdown" />
        </div>
      </div>

      <footer class="border-t border-zinc-200 bg-white px-4 py-3">
        <div class="mb-2 flex items-center justify-between text-xs text-zinc-500">
          <span>Subtask {{ store.currentSubtask || 0 }} / {{ store.totalSubtasks || 0 }}</span>
          <span>{{ progress }}%</span>
        </div>
        <div class="h-2 overflow-hidden rounded bg-zinc-200">
          <div class="h-full bg-emerald-600 transition-all" :style="{ width: `${progress}%` }"></div>
        </div>
        <p v-if="store.error" class="mt-2 text-sm text-red-700">{{ store.error }}</p>
      </footer>
    </section>
  </main>
</template>
