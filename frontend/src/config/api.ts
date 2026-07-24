export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/** Header required by the API in production for mutating requests (CSRF). */
export const CSRF_HEADERS = {
  'X-Requested-With': 'XMLHttpRequest',
} as const
