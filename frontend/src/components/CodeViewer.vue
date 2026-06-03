<script setup lang="ts">
import { computed } from 'vue'
import hljs from 'highlight.js'
import { Clipboard } from '@lucide/vue'

const props = defineProps<{
  code: string
}>()

const highlighted = computed(() => {
  if (!props.code) return ''
  return hljs.highlight(props.code, { language: 'python' }).value
})

async function copyCode() {
  if (!props.code) return
  await navigator.clipboard.writeText(props.code)
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex h-10 items-center justify-between border-b border-zinc-200 px-3">
      <span class="text-sm font-semibold text-zinc-800">Generated Python</span>
      <button
        class="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-40"
        :disabled="!code"
        type="button"
        @click="copyCode"
      >
        <Clipboard class="h-3.5 w-3.5" />
        Copy
      </button>
    </div>
    <pre v-if="code" class="min-h-0 flex-1 overflow-auto bg-zinc-950 p-4 text-sm text-zinc-100"><code v-html="highlighted"></code></pre>
    <div v-else class="flex flex-1 items-center justify-center text-sm text-zinc-500">No code yet</div>
  </div>
</template>
