const DEV_API_URL = 'http://localhost:8000'

function resolveApiUrl(): string {
  const configured = import.meta.env.VITE_API_URL?.trim()
  if (configured) {
    return configured.replace(/\/$/, '')
  }
  if (import.meta.env.DEV) {
    return DEV_API_URL
  }
  throw new Error(
    'Missing VITE_API_URL. Set it in Vercel environment variables or frontend/.env.production, then redeploy.',
  )
}

export const API_URL = resolveApiUrl()

/** Header required by the API in production for mutating requests (CSRF). */
export const CSRF_HEADERS = {
  'X-Requested-With': 'XMLHttpRequest',
} as const
