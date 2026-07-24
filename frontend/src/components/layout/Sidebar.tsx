import { useMemo, useState } from 'react'
import { NavLink, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useProjects } from '../../contexts/ProjectsContext'
import type { Project } from '../../types/project'
import {
  groupRecentProjects,
  RECENT_VISIBLE_LIMIT,
} from '../../utils/projectNav'
import {
  readRecentExpanded,
  writeRecentExpanded,
} from '../../utils/sidebarStorage'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ClockIcon,
  FolderIcon,
  HomeIcon,
  LogoutIcon,
  PlusIcon,
  SettingsIcon,
  StarIcon,
} from '../icons/NavIcons'
import { YelloBotLogo } from '../brand/YelloBotLogo'
import { ThemeToggle } from '../ui/ThemeToggle'
import { ProjectNavItem } from './ProjectNavItem'
import { authApi } from '../../api/auth'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapsed: () => void
  onNavigate?: () => void
}

function SectionLabel({ icon: Icon, label, collapsed }: { icon: typeof HomeIcon; label: string; collapsed: boolean }) {
  if (collapsed) return <div className="my-2 h-px bg-zinc-800/80" />
  return (
    <div className="mb-1.5 mt-3 flex items-center gap-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
      <Icon className="h-3.5 w-3.5 opacity-70" />
      {label}
    </div>
  )
}

function renderRecentList(
  projects: Project[],
  activeProjectId: string | null,
  collapsed: boolean,
  expanded: boolean,
  onNavigate?: () => void,
) {
  const visible = expanded ? projects : projects.slice(0, RECENT_VISIBLE_LIMIT)

  if (!expanded) {
    return (
      <div className="space-y-0.5">
        {visible.map((project) => (
          <ProjectNavItem
            key={project.id}
            project={project}
            activeProjectId={activeProjectId}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    )
  }

  const groups = groupRecentProjects(visible)
  return (
    <div className="space-y-2">
      {groups.map((group) => (
        <div key={group.label}>
          {!collapsed && (
            <p className="mb-1 px-3 text-[10px] font-medium uppercase tracking-wide text-zinc-600">
              {group.label}
            </p>
          )}
          <div className="space-y-0.5">
            {group.projects.map((project) => (
              <ProjectNavItem
                key={project.id}
                project={project}
                activeProjectId={activeProjectId}
                collapsed={collapsed}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export function Sidebar({ collapsed, onToggleCollapsed, onNavigate }: SidebarProps) {
  const { user, clearSession } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const params = useParams()
  const { pinnedProjects, recentProjects, loading, createProject } = useProjects()
  const [recentExpanded, setRecentExpanded] = useState(readRecentExpanded)
  const [creating, setCreating] = useState(false)

  const activeProjectId = location.pathname.startsWith('/projects/')
    ? (params.id ?? null)
    : null

  const hasProjects = pinnedProjects.length + recentProjects.length > 0
  const showMoreVisible = !recentExpanded && recentProjects.length > RECENT_VISIBLE_LIMIT

  const initials = useMemo(
    () =>
      user?.name
        ?.split(' ')
        .map((n) => n[0])
        .join('')
        .slice(0, 2)
        .toUpperCase(),
    [user?.name],
  )

  async function handleLogout() {
    try {
      await authApi.logout()
    } finally {
      clearSession()
      navigate('/login')
    }
  }

  async function handleQuickCreate() {
    setCreating(true)
    try {
      const created = await createProject({
        name: 'New Project',
        description: '',
        system_prompt: '',
      })
      navigate(`/projects/${created.id}`)
      onNavigate?.()
    } finally {
      setCreating(false)
    }
  }

  function toggleRecentExpanded() {
    setRecentExpanded((prev) => {
      const next = !prev
      writeRecentExpanded(next)
      return next
    })
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-150 ${
      collapsed ? 'justify-center px-2.5' : ''
    } ${
      isActive
        ? 'bg-sidebar-active text-white shadow-sm'
        : 'text-zinc-400 hover:bg-sidebar-hover hover:text-zinc-200'
    }`

  return (
    <div className="flex h-full flex-col bg-sidebar">
      <div className={`flex h-[76px] items-center ${collapsed ? 'justify-center px-1' : 'justify-between pl-3 pr-4'}`}>
        <div className={`flex min-w-0 items-center ${collapsed ? '-ml-0.5 justify-center' : 'ml-1'}`}>
          <YelloBotLogo tone="dark" size="md" compact={collapsed} />
        </div>
        {!collapsed && (
          <ThemeToggle className="!border-zinc-700 !bg-zinc-800 !text-zinc-300 hover:!bg-zinc-700 hover:!text-white" />
        )}
      </div>

      <nav className="flex min-h-0 flex-1 flex-col px-3 pt-1">
        <NavLink to="/home" end className={navLinkClass} onClick={onNavigate} title="Home">
          <HomeIcon className="h-[18px] w-[18px] flex-shrink-0 opacity-80" />
          {!collapsed && 'Home'}
        </NavLink>

        <div className="my-2 h-px bg-zinc-800/80" />

        {!collapsed && !loading && !hasProjects && (
          <div className="rounded-xl border border-dashed border-zinc-700 px-3 py-4 text-center">
            <p className="text-[12px] text-zinc-500">No recent projects</p>
            <button
              type="button"
              onClick={() => void handleQuickCreate()}
              disabled={creating}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-[12px] font-semibold text-zinc-900 transition hover:bg-brand-hover disabled:opacity-60"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Create Project
            </button>
          </div>
        )}

        {(pinnedProjects.length > 0 || (!collapsed && hasProjects)) && (
          <>
            <SectionLabel icon={StarIcon} label="Pinned" collapsed={collapsed} />
            {pinnedProjects.length > 0 ? (
              <div className="space-y-0.5">
                {pinnedProjects.map((project) => (
                  <ProjectNavItem
                    key={project.id}
                    project={project}
                    activeProjectId={activeProjectId}
                    collapsed={collapsed}
                    onNavigate={onNavigate}
                  />
                ))}
              </div>
            ) : (
              !collapsed && (
                <p className="px-3 pb-1 text-[11px] text-zinc-600">Pin projects from the ⋯ menu</p>
              )
            )}
          </>
        )}

        {recentProjects.length > 0 && (
          <>
            <SectionLabel icon={ClockIcon} label="Recent" collapsed={collapsed} />
            {renderRecentList(
              recentProjects,
              activeProjectId,
              collapsed,
              recentExpanded,
              onNavigate,
            )}
            {!collapsed && showMoreVisible && (
              <button
                type="button"
                onClick={toggleRecentExpanded}
                className="mt-1 w-full rounded-xl px-3 py-2 text-left text-[12px] font-medium text-zinc-500 transition hover:bg-sidebar-hover hover:text-zinc-300"
              >
                + Show More
              </button>
            )}
            {!collapsed && recentExpanded && recentProjects.length > RECENT_VISIBLE_LIMIT && (
              <button
                type="button"
                onClick={toggleRecentExpanded}
                className="mt-1 w-full rounded-xl px-3 py-2 text-left text-[12px] font-medium text-zinc-500 transition hover:bg-sidebar-hover hover:text-zinc-300"
              >
                Show Less
              </button>
            )}
          </>
        )}

        <div className="my-2 h-px bg-zinc-800/80" />

        <NavLink to="/home" end className={navLinkClass} onClick={onNavigate} title="Projects">
          <FolderIcon className="h-[18px] w-[18px] flex-shrink-0 opacity-80" />
          {!collapsed && 'Projects'}
        </NavLink>
        <NavLink to="/settings" className={navLinkClass} onClick={onNavigate} title="Settings">
          <SettingsIcon className="h-[18px] w-[18px] flex-shrink-0 opacity-80" />
          {!collapsed && 'Settings'}
        </NavLink>

        <div className="mt-auto" />
      </nav>

      <div className="border-t border-zinc-800/80 p-3">
        <div
          className={`flex items-center rounded-xl bg-sidebar-hover ${
            collapsed ? 'justify-center p-2' : 'gap-3 px-3 py-2.5'
          }`}
        >
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-brand text-xs font-bold text-zinc-900">
            {initials || '?'}
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-medium text-zinc-200">{user?.name}</p>
              <p className="truncate text-[11px] text-zinc-500">{user?.email}</p>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={() => void handleLogout()}
              title="Logout"
              className="flex-shrink-0 rounded-lg p-1.5 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-300"
            >
              <LogoutIcon />
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={onToggleCollapsed}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="mt-2 flex w-full items-center justify-center rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-300"
        >
          {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
        </button>
      </div>
    </div>
  )
}
