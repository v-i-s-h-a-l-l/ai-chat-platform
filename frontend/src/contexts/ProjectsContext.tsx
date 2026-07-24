import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { projectApi } from '../api/projects'
import { getErrorMessage } from '../api/client'
import type { Project, ProjectCreate, ProjectUpdate } from '../types/project'
import {
  selectPinnedProjects,
  selectRecentProjects,
  sortProjectsForNav,
} from '../utils/projectNav'
import { writeActiveProjectId } from '../utils/sidebarStorage'

interface ProjectsContextValue {
  projects: Project[]
  pinnedProjects: Project[]
  recentProjects: Project[]
  loading: boolean
  error: string | null
  refreshProjects: () => Promise<void>
  createProject: (data: ProjectCreate) => Promise<Project>
  updateProject: (id: string, data: ProjectUpdate) => Promise<Project>
  deleteProject: (id: string) => Promise<void>
  duplicateProject: (id: string) => Promise<Project>
  markProjectOpened: (project: Project) => void
  setError: (message: string | null) => void
}

const ProjectsContext = createContext<ProjectsContextValue | null>(null)

function upsertProject(list: Project[], project: Project): Project[] {
  const next = list.filter((p) => p.id !== project.id)
  next.push(project)
  return sortProjectsForNav(next)
}

export function ProjectsProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const loadedRef = useRef(false)

  const refreshProjects = useCallback(async () => {
    try {
      const data = await projectApi.list()
      setProjects(sortProjectsForNav(data))
      setError(null)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (loadedRef.current) return
    loadedRef.current = true
    void refreshProjects()
  }, [refreshProjects])

  const markProjectOpened = useCallback((project: Project) => {
    writeActiveProjectId(project.id)
    setProjects((prev) => {
      const accessedAt = project.last_accessed_at ?? new Date().toISOString()
      const touched: Project = { ...project, last_accessed_at: accessedAt }
      const next = upsertProject(prev, touched)
      if (next.length === prev.length && next.every((p, i) => p.id === prev[i]?.id)) {
        return prev
      }
      return next
    })
  }, [])

  const createProject = useCallback(async (data: ProjectCreate) => {
    const created = await projectApi.create(data)
    setProjects((prev) => upsertProject(prev, created))
    return created
  }, [])

  const updateProject = useCallback(async (id: string, data: ProjectUpdate) => {
    const updated = await projectApi.update(id, data)
    setProjects((prev) => upsertProject(prev, updated))
    return updated
  }, [])

  const duplicateProject = useCallback(async (id: string) => {
    const copy = await projectApi.duplicate(id)
    setProjects((prev) => upsertProject(prev, copy))
    return copy
  }, [])

  const deleteProject = useCallback(async (id: string) => {
    await projectApi.delete(id)
    setProjects((prev) => prev.filter((p) => p.id !== id))
  }, [])

  const pinnedProjects = useMemo(() => selectPinnedProjects(projects), [projects])
  const recentProjects = useMemo(() => selectRecentProjects(projects), [projects])

  const value = useMemo(
    () => ({
      projects,
      pinnedProjects,
      recentProjects,
      loading,
      error,
      refreshProjects,
      createProject,
      updateProject,
      deleteProject,
      duplicateProject,
      markProjectOpened,
      setError,
    }),
    [
      projects,
      pinnedProjects,
      recentProjects,
      loading,
      error,
      refreshProjects,
      createProject,
      updateProject,
      deleteProject,
      duplicateProject,
      markProjectOpened,
    ],
  )

  return <ProjectsContext.Provider value={value}>{children}</ProjectsContext.Provider>
}

export function useProjects() {
  const ctx = useContext(ProjectsContext)
  if (!ctx) throw new Error('useProjects must be used within ProjectsProvider')
  return ctx
}

export function useProjectsOptional() {
  return useContext(ProjectsContext)
}
