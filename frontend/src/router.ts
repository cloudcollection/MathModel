import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import TaskView from './views/TaskView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/task/:taskId', component: TaskView },
  ],
})

