import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

function AuthLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
    </div>
  )
}

export function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) return <AuthLoading />
  if (!user) return <Navigate to="/login" replace />

  return <Outlet />
}

export function PublicRoute() {
  const { user, loading } = useAuth()

  // Render login/register immediately — don't block public pages on session check.
  if (!loading && user) return <Navigate to="/home" replace />

  return <Outlet />
}
