import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { useAuth } from '../../contexts/AuthContext'
import { ProtectedRoute } from './ProtectedRoute'

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

describe('ProtectedRoute', () => {
  it('redirects unauthenticated users to login', () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      loading: false,
      refreshSession: vi.fn(),
      clearSession: vi.fn(),
      setUser: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/home" element={<div>Secret</div>} />
          </Route>
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('renders child routes for authenticated users', () => {
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: '1',
        email: 'user@example.com',
        name: 'User',
        preferred_llm_model: null,
      },
      loading: false,
      refreshSession: vi.fn(),
      clearSession: vi.fn(),
      setUser: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/home" element={<div>Secret</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Secret')).toBeInTheDocument()
  })
})
