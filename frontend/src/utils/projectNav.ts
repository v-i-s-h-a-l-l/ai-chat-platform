import type { Project } from '../types/project'

export const RECENT_VISIBLE_LIMIT = 6

export type RecencyGroup = 'Today' | 'Yesterday' | 'Last 7 Days' | 'Older'

export function projectAccessTime(project: Project): number {
  const ts = project.last_accessed_at ?? project.created_at
  return new Date(ts).getTime()
}

export function sortProjectsForNav(projects: Project[]): Project[] {
  return [...projects].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
    return projectAccessTime(b) - projectAccessTime(a)
  })
}

export function selectPinnedProjects(projects: Project[]): Project[] {
  return projects.filter((p) => p.is_pinned).sort((a, b) => projectAccessTime(b) - projectAccessTime(a))
}

export function selectRecentProjects(projects: Project[]): Project[] {
  return projects
    .filter((p) => !p.is_pinned)
    .sort((a, b) => projectAccessTime(b) - projectAccessTime(a))
}

export function groupRecentProjects(projects: Project[]): { label: RecencyGroup; projects: Project[] }[] {
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfYesterday = new Date(startOfToday)
  startOfYesterday.setDate(startOfYesterday.getDate() - 1)
  const startOfWeek = new Date(startOfToday)
  startOfWeek.setDate(startOfWeek.getDate() - 7)

  const buckets: Record<RecencyGroup, Project[]> = {
    Today: [],
    Yesterday: [],
    'Last 7 Days': [],
    Older: [],
  }

  for (const project of projects) {
    const accessed = new Date(project.last_accessed_at ?? project.created_at)
    if (accessed >= startOfToday) {
      buckets.Today.push(project)
    } else if (accessed >= startOfYesterday) {
      buckets.Yesterday.push(project)
    } else if (accessed >= startOfWeek) {
      buckets['Last 7 Days'].push(project)
    } else {
      buckets.Older.push(project)
    }
  }

  return (Object.keys(buckets) as RecencyGroup[])
    .map((label) => ({ label, projects: buckets[label] }))
    .filter((group) => group.projects.length > 0)
}

export function projectInitial(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return '?'
  return trimmed.charAt(0).toUpperCase()
}

export function projectAccentClass(seed: string): string {
  const palette = [
    'from-amber-400 to-yellow-500',
    'from-yellow-500 to-amber-600',
    'from-amber-500 to-orange-500',
    'from-lime-500 to-yellow-500',
    'from-orange-400 to-amber-500',
    'from-yellow-400 to-amber-500',
  ]
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash + seed.charCodeAt(i) * (i + 1)) % palette.length
  }
  return palette[hash]
}
