import axios from 'axios'

import { API_URL, CSRF_HEADERS } from '../config/api'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** Skip the 401 → /auth/refresh retry (used for initial session bootstrap). */
    skipAuthRefresh?: boolean
  }
}

const DEFAULT_TIMEOUT_MS = 60_000

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  timeout: DEFAULT_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
    ...CSRF_HEADERS,
  },
})

let isRefreshing = false
let refreshPromise: Promise<void> | null = null

async function refreshSession(): Promise<void> {
  await api.post('/auth/refresh')
}

/**
 * Single-flight token refresh — shared by the axios interceptor below and by
 * streamChat.ts (which bypasses axios via `fetch` for SSE and needs the same
 * de-duplicated refresh-then-retry behavior on a 401).
 */
export function refreshAccessToken(): Promise<void> {
  if (!isRefreshing) {
    isRefreshing = true
    refreshPromise = refreshSession().finally(() => {
      isRefreshing = false
      refreshPromise = null
    })
  }
  return refreshPromise!
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.skipAuthRefresh &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/register') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      originalRequest._retry = true

      try {
        await refreshAccessToken()
        return api(originalRequest)
      } catch {
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

function getTimeoutMessage(config?: axios.InternalAxiosRequestConfig): string {
  const url = config?.url ?? ''
  if (url.includes('/documents')) {
    return 'Upload timed out. The file may still be processing — check the document list in a moment.'
  }
  if (url.includes('/auth/') || url.includes('/users/me')) {
    return 'The server is taking longer than usual to respond. Please wait a moment and try again.'
  }
  return 'Request timed out. Please try again in a moment.'
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        return getTimeoutMessage(error.config)
      }
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        return 'Cannot reach the server. Make sure the backend is running on port 8000 and PostgreSQL (Docker) is started.'
      }
      return normalizeErrorText(error.message)
    }
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return normalizeErrorText(detail)
    if (typeof detail === 'object' && detail !== null && 'message' in detail) {
      const message = (detail as { message?: unknown }).message
      if (typeof message === 'string') return normalizeErrorText(message)
    }
    if (Array.isArray(detail)) return detail.map((d) => d.msg ?? d).join(', ')
    if (error.response.status >= 500) {
      return 'Server error. Check that PostgreSQL is running (Docker Desktop → docker compose up -d).'
    }
    return normalizeErrorText(error.message)
  }
  if (error instanceof Error) return normalizeErrorText(error.message)
  return 'An unexpected error occurred'
}

function normalizeErrorText(text: string): string {
  const groqMatch = text.match(/Groq API error \(\d+\):\s*([\s\S]+)/)
  if (groqMatch) {
    const payload = groqMatch[1].trim()
    try {
      const parsed = JSON.parse(payload) as { error?: { message?: string }; message?: string }
      const inner = parsed.error?.message ?? parsed.message
      if (typeof inner === 'string' && inner.trim()) {
        return inner.trim()
      }
    } catch {
      // Keep readable fallback below
    }
  }
  return text
}
