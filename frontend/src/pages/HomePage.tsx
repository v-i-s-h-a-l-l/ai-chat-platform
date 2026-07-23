import { useCallback, useEffect, useState } from 'react'
import { projectApi } from '../api/projects'
import { getErrorMessage } from '../api/client'
import { CreateProjectModal } from '../components/projects/CreateProjectModal'
import { ProjectCard } from '../components/projects/ProjectCard'
import { PlusIcon } from '../components/icons/NavIcons'
import { Button } from '../components/ui/Button'
import { useAuth } from '../contexts/AuthContext'
import type { Project } from '../types/project'

export function HomePage() {
  const { user } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [error, setError] = useState('')

  const fetchProjects = useCallback(async () => {
    try {
      const data = await projectApi.list()
      setProjects(data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  async function handleCreate(data: {
    name: string
    description: string
    system_prompt: string
  }) {
    await projectApi.create(data)
    await fetchProjects()
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this project and all its conversations?')) return
    try {
      await projectApi.delete(id)
      setProjects((prev) => prev.filter((p) => p.id !== id))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-violet-200 border-t-violet-600" />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Page header */}
        <div className="mb-8">
          <p className="text-[13px] font-medium text-violet-600">{greeting()}</p>
          <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                {user?.name ? `${user.name.split(' ')[0]}'s Projects` : 'My Projects'}
              </h1>
              <p className="mt-1 text-[13px] text-zinc-500">
                {projects.length === 0
                  ? 'Create your first AI chatbot project to get started'
                  : `${projects.length} project${projects.length !== 1 ? 's' : ''} · powered by Groq`}
              </p>
            </div>
            <Button onClick={() => setModalOpen(true)}>
              <PlusIcon />
              New Project
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
            {error}
          </div>
        )}

        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white py-20 text-center dark:border-zinc-700 dark:bg-zinc-900">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-50 to-indigo-100">
              <PlusIcon className="h-6 w-6 text-violet-600" />
            </div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">No projects yet</h3>
            <p className="mt-1.5 max-w-sm text-[13px] text-zinc-500">
              Build your first chatbot with a custom system prompt and persistent memory.
            </p>
            <Button className="mt-6" onClick={() => setModalOpen(true)}>
              <PlusIcon />
              Create your first project
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard key={project.id} project={project} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>

      <CreateProjectModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreate}
      />
    </div>
  )
}
