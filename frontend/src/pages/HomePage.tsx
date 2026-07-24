import { useState } from 'react'
import { getErrorMessage } from '../api/client'
import { CreateProjectModal } from '../components/projects/CreateProjectModal'
import { ProjectCard } from '../components/projects/ProjectCard'
import { PlusIcon } from '../components/icons/NavIcons'
import { Button } from '../components/ui/Button'
import { useAuth } from '../contexts/AuthContext'
import { useProjects } from '../contexts/ProjectsContext'

export function HomePage() {
  const { user } = useAuth()
  const { projects, loading, error, createProject, deleteProject, setError } = useProjects()
  const [modalOpen, setModalOpen] = useState(false)

  async function handleCreate(data: {
    name: string
    description: string
    system_prompt: string
  }) {
    try {
      await createProject(data)
    } catch (err) {
      setError(getErrorMessage(err))
      throw err
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this project and all its conversations?')) return
    try {
      await deleteProject(id)
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
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-amber-200 border-t-brand" />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-8">
          <p className="text-[13px] font-medium text-amber-700 dark:text-amber-400">{greeting()}</p>
          <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                {user?.name ? `${user.name.split(' ')[0]}'s Projects` : 'My Projects'}
              </h1>
              <p className="mt-1 text-[13px] text-zinc-500">
                {projects.length === 0
                  ? 'Create your first YelloBot project to get started'
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
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
            <button
              type="button"
              onClick={() => setError(null)}
              className="ml-2 underline hover:no-underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white py-20 text-center dark:border-zinc-700 dark:bg-zinc-900">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-50 to-yellow-100 dark:from-amber-950/40 dark:to-yellow-950/30">
              <PlusIcon className="h-6 w-6 text-amber-700 dark:text-amber-400" />
            </div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">No projects yet</h3>
            <p className="mt-1.5 max-w-sm text-[13px] text-zinc-500">
              Build your first project with YelloBot — custom system prompts and persistent memory.
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
