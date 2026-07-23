import { useNavigate } from 'react-router-dom'
import type { Project } from '../../types/project'
import { MessageIcon, TrashIcon } from '../icons/NavIcons'
import { Button } from '../ui/Button'

interface ProjectCardProps {
  project: Project
  onDelete: (id: string) => void
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const navigate = useNavigate()

  const formattedDate = new Date(project.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

  return (
    <article className="group relative flex flex-col rounded-2xl border border-zinc-200/80 bg-white p-5 shadow-sm transition-all duration-200 hover:border-violet-200 hover:shadow-md hover:shadow-violet-500/5 dark:border-zinc-700/80 dark:bg-zinc-900 dark:hover:border-violet-700">
      {/* Icon header */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-50 to-indigo-100 text-violet-600 transition group-hover:from-violet-100 group-hover:to-indigo-200">
          <MessageIcon className="h-5 w-5" />
        </div>
        <button
          onClick={() => onDelete(project.id)}
          className="rounded-lg p-1.5 text-zinc-300 opacity-0 transition hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
          title="Delete project"
        >
          <TrashIcon className="h-4 w-4" />
        </button>
      </div>

      <h3 className="text-[15px] font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">{project.name}</h3>
      <p className="mt-1.5 flex-1 text-[13px] leading-relaxed text-zinc-500 line-clamp-2">
        {project.description || 'No description provided'}
      </p>

      <div className="mt-4 flex items-center justify-between border-t border-zinc-100 pt-4">
        <span className="text-[11px] text-zinc-400">{formattedDate}</span>
        <Button
          size="sm"
          onClick={() => navigate(`/projects/${project.id}`)}
        >
          Open →
        </Button>
      </div>
    </article>
  )
}
