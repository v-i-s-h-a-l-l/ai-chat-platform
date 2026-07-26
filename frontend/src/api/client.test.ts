import axios from 'axios'
import { describe, expect, it } from 'vitest'

import { getErrorMessage } from '../api/client'
import { API_URL, CSRF_HEADERS } from '../config/api'

describe('getErrorMessage', () => {
  it('returns network guidance when the server is unreachable', () => {
    const error = new axios.AxiosError('Network Error', 'ERR_NETWORK')
    expect(getErrorMessage(error)).toContain('Cannot reach the server')
  })

  it('returns server detail for 401 responses', () => {
    const error = new axios.AxiosError('Unauthorized', '401', undefined, undefined, {
      status: 401,
      statusText: 'Unauthorized',
      headers: {},
      config: { headers: new axios.AxiosHeaders() },
      data: { detail: 'Invalid email or password' },
    })
    expect(getErrorMessage(error)).toBe('Invalid email or password')
  })

  it('returns postgres guidance for 500 responses', () => {
    const error = new axios.AxiosError('Server Error', '500', undefined, undefined, {
      status: 500,
      statusText: 'Internal Server Error',
      headers: {},
      config: { headers: new axios.AxiosHeaders() },
      data: {},
    })
    expect(getErrorMessage(error)).toContain('Server error')
  })

  it('returns auth-specific guidance for login timeouts', () => {
    const error = new axios.AxiosError('timeout of 60000ms exceeded', 'ECONNABORTED', {
      headers: new axios.AxiosHeaders(),
      url: '/auth/login',
    } as axios.InternalAxiosRequestConfig)
    expect(getErrorMessage(error)).toContain('server is taking longer than usual')
  })
})

describe('api config', () => {
  it('exposes a default API URL', () => {
    expect(API_URL).toMatch(/^https?:\/\//)
  })

  it('includes CSRF headers for mutating requests', () => {
    expect(CSRF_HEADERS['X-Requested-With']).toBe('XMLHttpRequest')
  })
})
