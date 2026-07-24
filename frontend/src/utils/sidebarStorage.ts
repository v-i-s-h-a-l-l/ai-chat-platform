const SIDEBAR_COLLAPSED_KEY = 'sidebar:collapsed'
const SIDEBAR_RECENT_EXPANDED_KEY = 'sidebar:recentExpanded'
const ACTIVE_PROJECT_KEY = 'sidebar:activeProjectId'

function readBool(key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null) return fallback
    return raw === 'true'
  } catch {
    return fallback
  }
}

function writeBool(key: string, value: boolean) {
  try {
    localStorage.setItem(key, String(value))
  } catch {
    // ignore quota / private mode
  }
}

export function readSidebarCollapsed(): boolean {
  return readBool(SIDEBAR_COLLAPSED_KEY, false)
}

export function writeSidebarCollapsed(value: boolean) {
  writeBool(SIDEBAR_COLLAPSED_KEY, value)
}

export function readRecentExpanded(): boolean {
  return readBool(SIDEBAR_RECENT_EXPANDED_KEY, false)
}

export function writeRecentExpanded(value: boolean) {
  writeBool(SIDEBAR_RECENT_EXPANDED_KEY, value)
}

export function readActiveProjectId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_PROJECT_KEY)
  } catch {
    return null
  }
}

export function writeActiveProjectId(projectId: string | null) {
  try {
    if (projectId) localStorage.setItem(ACTIVE_PROJECT_KEY, projectId)
    else localStorage.removeItem(ACTIVE_PROJECT_KEY)
  } catch {
    // ignore
  }
}
