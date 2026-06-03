<script setup lang="ts">
import { useRouter } from 'vue-router'
import ProblemInput from '../components/ProblemInput.vue'
import { apiUrl } from '../lib/api'

const router = useRouter()

async function startTask(payload: { problemText: string; files: File[]; model: string }) {
  const form = new FormData()
  form.append('problem_text', payload.problemText)
  if (payload.model.trim()) form.append('model', payload.model.trim())
  payload.files.forEach((file) => form.append('files', file))

  const response = await fetch(apiUrl('/api/task'), {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  const data = await response.json()
  await router.push(`/task/${data.task_id}`)
}
</script>

<template>
  <ProblemInput @submit="startTask" />
</template>

