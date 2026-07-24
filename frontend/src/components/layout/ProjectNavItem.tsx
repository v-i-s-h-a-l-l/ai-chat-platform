import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/client'
import { useProjects } from '../../contexts/ProjectsContext'
import type { Project } from '../../types/project'
import { projectAccentClass, projectInitial } from '../../utils/projectNav'
import {
  CopyIcon,
  DotsHorizontalIcon,
  PencilIcon,
  StarIcon,
  TrashIcon,
} from '../icons/NavIcons'
import { RenameProjectModal } from './RenameProjectModal'

interface ProjectNavItemProps {
  project: Project
  activeProjectId: string | null
  collapsed?: boolean
  onNavigate?: () => void
}

export function ProjectNavItem({
  project,
  activeProjectId,
  collapsed = false,
  onNavigate,
}: ProjectNavItemProps) {
  const navigate = useNavigate()
  const { markProjectOpened, updateProject, duplicateProject, deleteProject, setError } =
    useProjects()
  const [menuOpen, setMenuOpen] = useState(false)
  const [renameOpen, setRenameOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const isActive = activeProjectId === project.id

  useEffect(() => {
    if (!menuOpen) return
    function onPointerDown(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [menuOpen])

  async function runAction(action: () => Promise<void>) {
    setBusy(true)
    try {
      await action()
      setMenuOpen(false)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  function handleOpen() {
    markProjectOpened(project)
    onNavigate?.()
  }

  return (
    <>
      <div
        className={`group relative flex items-center gap-2 rounded-xl transition-all duration-150 ${
          isActive
            ? 'border border-amber-500/40 bg-sidebar-active shadow-sm'
            : 'border border-transparent hover:bg-sidebar-hover'
        }`}
      >
        <NavLink
          to={`/projects/${project.id}`}
          onClick={handleOpen}
          title={project.name}
          className={`flex min-w-0 flex-1 items-center gap-2.5 px-2.5 py-2 ${
            isActive ? 'font-semibold text-white' : 'font-medium text-zinc-300 hover:text-zinc-100'
          }`}
        >
          <span
            className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-[11px] font-bold text-white ${projectAccentClass(project.id)}`}
          >
            {projectInitial(project.name)}
          </span>
          {!collapsed && (
            <span className="truncate text-[13px] leading-none">{project.name}</span>
          )}
          {!collapsed && isActive && (
            <span className="ml-auto h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-400" aria-hidden />
          )}
        </NavLink>

        {!collapsed && (
          <div ref={menuRef} className="relative mr-1.5 flex-shrink-0">
            <button
              type="button"
              aria-label={`Actions for ${project.name}`}
              onClick={() => setMenuOpen((open) => !open)}
              className={`rounded-lg p-1 text-zinc-500 opacity-0 transition hover:bg-zinc-800 hover:text-zinc-200 focus-visible:opacity-100 group-hover:opacity-100 ${
                menuOpen ? 'opacity-100' : ''
              }`}
            >
              <DotsHorizontalIcon />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full z-50 mt-1 min-w-[160px] overflow-hidden rounded-xl border border-zinc-700 bg-zinc-900 py-1 shadow-xl">
                <button
                  type="button"
                  disabled={busy}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-zinc-200 hover:bg-zinc-800"
                  onClick={() => {
                    setRenameOpen(true)
                    setMenuOpen(false)
                  }}
                >
                  <PencilIcon className="h-3.5 w-3.5" />
                  Rename
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-zinc-200 hover:bg-zinc-800"
                  onClick={() =>
                    void runAction(async () => {
                      await updateProject(project.id, { is_pinned: !project.is_pinned })
                    })
                  }
                >
                  <StarIcon className="h-3.5 w-3.5" />
                  {project.is_pinned ? 'Unpin' : 'Pin'}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-zinc-200 hover:bg-zinc-800"
                  onClick={() =>
                    void runAction(async () => {
                      const copy = await duplicateProject(project.id)
                      navigate(`/projects/${copy.id}`)
                      markProjectOpened(copy)
                      onNavigate?.()
                    })
                  }
                >
                  <CopyIcon className="h-3.5 w-3.5" />
                  Duplicate
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-red-400 hover:bg-red-950/40"
                  onClick={() =>
                    void runAction(async () => {
                      if (!confirm(`Delete "${project.name}" and all its conversations?`)) return
                      await deleteProject(project.id)
                      if (isActive) navigate('/home')
                    })
                  }
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                  Delete
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <RenameProjectModal
        open={renameOpen}
        initialName={project.name}
        loading={busy}
        onClose={() => setRenameOpen(false)}
        onSubmit={async (name) => {
          await runAction(async () => {
            await updateProject(project.id, { name })
            setRenameOpen(false)
          })
        }}
      />
    </>
  )
}
