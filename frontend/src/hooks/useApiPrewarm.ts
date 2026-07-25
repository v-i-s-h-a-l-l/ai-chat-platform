import { useEffect } from 'react'

import { prewarmApi } from '../api/prewarm'

/** Ping /health on mount so auth requests hit a warm backend. */
export function useApiPrewarm(): void {
  useEffect(() => {
    prewarmApi()
  }, [])
}
