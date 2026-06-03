export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

export function wsUrl(path: string): string {
  const url = new URL(API_BASE)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${url.origin}${path}`
}

