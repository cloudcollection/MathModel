<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'

const props = defineProps<{
  markdown: string
}>()

marked.use(
  markedKatex({
    throwOnError: false,
  }),
)

const html = computed(() => {
  if (!props.markdown) return ''
  return DOMPurify.sanitize(
    marked.parse(props.markdown, {
      async: false,
      gfm: true,
      breaks: true,
    }) as string,
  )
})
</script>

<template>
  <article v-if="markdown" class="prose max-w-none overflow-auto p-5" v-html="html"></article>
  <div v-else class="flex h-full items-center justify-center text-sm text-zinc-500">No paper yet</div>
</template>

