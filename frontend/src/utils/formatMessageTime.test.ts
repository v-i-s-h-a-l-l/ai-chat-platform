import { describe, expect, it, vi, afterEach } from 'vitest'

import { formatActivityLogTime, formatMessageTime } from './formatMessageTime'

describe('formatMessageTime', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns time only for today', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-24T12:00:00Z'))

    const result = formatMessageTime('2026-07-24T10:30:00Z')
    expect(result).toMatch(/\d/)
    expect(result).not.toContain('Jul')
  })

  it('returns date and time for older messages', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-24T12:00:00Z'))

    const result = formatMessageTime('2026-07-20T10:30:00Z')
    expect(result).toContain('Jul')
  })

  it('returns null for invalid input', () => {
    expect(formatMessageTime(undefined)).toBeNull()
    expect(formatMessageTime('not-a-date')).toBeNull()
  })
})

describe('formatActivityLogTime', () => {
  it('formats as HH:MM:SS', () => {
    const result = formatActivityLogTime('2026-07-24T14:05:09.000Z')
    expect(result).toMatch(/^\d{2}:\d{2}:\d{2}$/)
  })
})
