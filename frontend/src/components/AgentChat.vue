<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import { marked } from 'marked'
import type { AgentName, LogEntry } from '../types/ws'

const props = defineProps<{
  messages: LogEntry[]
  activeAgents: Partial<Record<AgentName, boolean>>
}>()

const feed = ref<HTMLElement | null>(null)

const badgeClass: Record<AgentName, string> = {
  system: 'bg-zinc-700 text-white',
  planner: 'bg-blue-100 text-blue-800',
  coder: 'bg-emerald-100 text-emerald-800',
  analyst: 'bg-amber-100 text-amber-900',
  writer: 'bg-violet-100 text-violet-800',
}

function render(content: string): string {
  const html = marked.parse(content, {
    async: false,
    gfm: true,
    breaks: true,
  }) as string
  return DOMPurify.sanitize(html)
}

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const activeList = computed(() =>
  Object.entries(props.activeAgents)
    .filter(([, value]) => value)
    .map(([agent]) => agent),
)

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (feed.value) feed.value.scrollTop = feed.value.scrollHeight
    document.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block as HTMLElement))
  },
)
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col border-r border-zinc-800 bg-zinc-950">
    <div class="flex h-12 items-center justify-between border-b border-zinc-800 px-4">
      <h2 class="text-sm font-semibold text-zinc-100">Agent Activity</h2>
      <div v-if="activeList.length" class="flex items-center gap-2 text-xs text-zinc-400">
        <span class="h-2 w-2 animate-pulse rounded-full bg-emerald-400"></span>
        {{ activeList.join(', ') }}
      </div>
    </div>

    <div ref="feed" class="min-h-0 flex-1 overflow-y-auto px-4 py-3">
      <div v-if="!messages.length" class="py-10 text-center text-sm text-zinc-500">Waiting for events</div>
      <article
        v-for="message in messages"
        :key="message.id"
        class="mb-3 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-3"
      >
        <header class="mb-2 flex items-center justify-between gap-3">
          <span class="rounded px-2 py-1 text-xs font-semibold uppercase" :class="badgeClass[message.agent]">
            {{ message.agent }}
          </span>
          <time class="text-xs text-zinc-500">{{ formatTime(message.timestamp) }}</time>
        </header>
        <div class="prose prose-invert max-w-none text-sm leading-6" v-html="render(message.content)"></div>
      </article>
    </div>
  </section>
</template>

