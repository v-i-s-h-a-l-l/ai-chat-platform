import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
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

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        return 'Cannot reach the server. Make sure the backend is running on port 8000 and PostgreSQL (Docker) is started.'
      }
      return error.message
    }
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg ?? d).join(', ')
    if (error.response.status >= 500) {
      return 'Server error. Check that PostgreSQL is running (Docker Desktop → docker compose up -d).'
    }
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred'
}
