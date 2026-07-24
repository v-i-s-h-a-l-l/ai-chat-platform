import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { ProjectsProvider } from '../../contexts/ProjectsContext'
import {
  readSidebarCollapsed,
  writeSidebarCollapsed,
} from '../../utils/sidebarStorage'
import { MenuIcon, XIcon } from '../icons/NavIcons'
import { YelloBotLogo } from '../brand/YelloBotLogo'
import { Sidebar } from './Sidebar'

function DashboardShell() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(readSidebarCollapsed)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev
      writeSidebarCollapsed(next)
      return next
    })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Desktop sidebar */}
      <aside
        className={`hidden flex-shrink-0 flex-col transition-[width] duration-200 ease-out lg:flex ${
          collapsed ? 'w-[72px]' : 'w-[260px]'
        }`}
      >
        <Sidebar collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-[280px] transform transition-transform duration-200 ease-out lg:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar collapsed={false} onToggleCollapsed={() => setMobileOpen(false)} onNavigate={() => setMobileOpen(false)} />
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="flex h-[60px] flex-shrink-0 items-center border-b border-zinc-200/80 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900 lg:hidden">
          <button
            type="button"
            aria-label="Open navigation menu"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-2 text-zinc-600 transition hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            <MenuIcon />
          </button>
          <YelloBotLogo size="sm" className="-ml-1" />
          {mobileOpen && (
            <button
              type="button"
              aria-label="Close navigation menu"
              onClick={() => setMobileOpen(false)}
              className="ml-auto rounded-lg p-2 text-zinc-600 dark:text-zinc-300"
            >
              <XIcon />
            </button>
          )}
        </div>

        <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-0 flex-1 flex-col">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export function DashboardLayout() {
  return (
    <ProjectsProvider>
      <DashboardShell />
    </ProjectsProvider>
  )
}
