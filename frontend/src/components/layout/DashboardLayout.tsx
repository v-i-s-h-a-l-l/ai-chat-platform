import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { useAuth } from '../../contexts/AuthContext'
import { ThemeToggle } from '../ui/ThemeToggle'
import {
  FolderIcon,
  HomeIcon,
  LogoutIcon,
  SettingsIcon,
  SparklesIcon,
} from '../icons/NavIcons'

const navItems = [
  { label: 'Home', to: '/home', icon: HomeIcon, end: true },
  { label: 'Projects', to: '/home', icon: FolderIcon, end: true },
  { label: 'Settings', to: '/settings', icon: SettingsIcon, end: false },
]

export function DashboardLayout() {
  const { user, clearSession } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const isChatPage = location.pathname.startsWith('/projects/')

  async function handleLogout() {
    try {
      await authApi.logout()
    } finally {
      clearSession()
      navigate('/login')
    }
  }

  const initials = user?.name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Sidebar */}
      <aside className="hidden w-[260px] flex-shrink-0 flex-col bg-sidebar lg:flex">
        {/* Logo */}
        <div className="flex h-[60px] items-center justify-between px-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg shadow-violet-500/20">
              <SparklesIcon className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-white">Chatbot</p>
              <p className="text-[11px] text-zinc-500">Platform</p>
            </div>
          </div>
          <ThemeToggle className="!border-zinc-700 !bg-zinc-800 !text-zinc-300 hover:!bg-zinc-700 hover:!text-white" />
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 px-3 pt-2">
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
            Menu
          </p>
          {navItems.map((item) => (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.end}
              className={({ isActive }) => {
                const active = isActive && !isChatPage
                return `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-150 ${
                  active
                    ? 'bg-sidebar-active text-white shadow-sm'
                    : 'text-zinc-400 hover:bg-sidebar-hover hover:text-zinc-200'
                }`
              }}
            >
              <item.icon className="h-[18px] w-[18px] flex-shrink-0 opacity-80" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="border-t border-zinc-800/80 p-3">
          <div className="flex items-center gap-3 rounded-xl bg-sidebar-hover px-3 py-2.5">
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 text-xs font-bold text-white">
              {initials || '?'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-medium text-zinc-200">{user?.name}</p>
              <p className="truncate text-[11px] text-zinc-500">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Logout"
              className="flex-shrink-0 rounded-lg p-1.5 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-300"
            >
              <LogoutIcon />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
