<script setup lang="ts">
import { computed, ref } from 'vue'
import { FileUp, Play, X } from '@lucide/vue'

const emit = defineEmits<{
  submit: [payload: { problemText: string; files: File[]; model: string }]
}>()

const problemText = ref('')
const files = ref<File[]>([])
const model = ref('')
const isDragging = ref(false)

const canSubmit = computed(() => problemText.value.trim().length > 0)

function addFiles(nextFiles: FileList | null) {
  if (!nextFiles) return
  files.value = [...files.value, ...Array.from(nextFiles)]
}

function removeFile(index: number) {
  files.value.splice(index, 1)
}

function onFileInput(event: Event) {
  addFiles((event.target as HTMLInputElement).files)
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  addFiles(event.dataTransfer?.files || null)
}

function submit() {
  if (!canSubmit.value) return
  emit('submit', {
    problemText: problemText.value,
    files: files.value,
    model: model.value,
  })
}
</script>

<template>
  <section class="mx-auto flex min-h-screen max-w-6xl flex-col gap-5 px-5 py-8">
    <header class="flex flex-col gap-2 border-b border-zinc-200 pb-5">
      <p class="text-sm font-semibold uppercase text-emerald-700">Math Modeling Agent</p>
      <h1 class="text-3xl font-semibold text-zinc-950">Competition Modeling Workspace</h1>
    </header>

    <div class="grid flex-1 gap-5 lg:grid-cols-[1fr_320px]">
      <div class="flex min-h-[520px] flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white">
        <div class="border-b border-zinc-200 px-4 py-3">
          <h2 class="text-sm font-semibold text-zinc-800">Problem Statement</h2>
        </div>
        <textarea
          v-model="problemText"
          class="min-h-[480px] flex-1 resize-none bg-white p-4 font-mono text-sm leading-6 text-zinc-900 outline-none"
          placeholder="Paste the full contest problem here..."
        />
      </div>

      <aside class="flex flex-col gap-4">
        <div class="rounded-lg border border-zinc-200 bg-white p-4">
          <label class="text-sm font-semibold text-zinc-800" for="model">Model</label>
          <input
            id="model"
            v-model="model"
            class="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
            list="model-presets"
            placeholder="Backend default"
          />
          <datalist id="model-presets">
            <option value="gpt-4.1" />
            <option value="deepseek/deepseek-chat" />
            <option value="gemini/gemini-2.5-pro" />
          </datalist>
        </div>

        <label
          class="flex min-h-[180px] cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-white p-5 text-center transition"
          :class="isDragging ? 'border-emerald-600 bg-emerald-50' : 'border-zinc-300'"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
        >
          <FileUp class="h-8 w-8 text-emerald-700" />
          <span class="text-sm font-medium text-zinc-800">Upload data files</span>
          <input class="hidden" multiple type="file" @change="onFileInput" />
        </label>

        <div v-if="files.length" class="rounded-lg border border-zinc-200 bg-white p-3">
          <ul class="flex flex-col gap-2">
            <li
              v-for="(file, index) in files"
              :key="`${file.name}-${index}`"
              class="flex items-center justify-between gap-2 rounded-md bg-zinc-100 px-3 py-2 text-sm"
            >
              <span class="truncate text-zinc-800">{{ file.name }}</span>
              <button class="text-zinc-500 hover:text-zinc-900" type="button" @click="removeFile(index)">
                <X class="h-4 w-4" />
              </button>
            </li>
          </ul>
        </div>

        <button
          class="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-zinc-950 px-4 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
          :disabled="!canSubmit"
          type="button"
          @click="submit"
        >
          <Play class="h-4 w-4" />
          Start
        </button>
      </aside>
    </div>
  </section>
</template>
