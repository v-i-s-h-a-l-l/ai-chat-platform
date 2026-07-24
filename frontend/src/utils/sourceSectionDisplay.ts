/**
 * Controls when the "Sources Used" markdown section is shown in the chat UI.
 * Backend still collects and stores sources; this only affects rendering.
 */

export interface SourceDisplayOptions {
  webSearchUsed?: boolean
  documentsUsed?: boolean
}

const SOURCES_HEADING_PATTERN = /^#{1,3}\s+Sources Used\s*$|^\*\*Sources Used\*\*\s*$/im

const EXTERNAL_SOURCE_INDICATORS = [
  /📄/,
  /uploaded documents?/i,
  /uploaded files?/i,
  /🌐/,
  /\binternet\b/i,
  /web search/i,
]

const GENERAL_KNOWLEDGE_INDICATORS = [/🧠/, /general knowledge/i]

const DOCUMENT_FILENAME_PATTERN =
  /\b[\w[\].\-()]+\.(pdf|docx?|txt|md|csv|xlsx?|pptx?|rtf)\b/i

function findSourcesSectionStart(content: string): number | null {
  const match = content.match(SOURCES_HEADING_PATTERN)
  return match?.index ?? null
}

function sectionBodyLines(section: string): string[] {
  const lines = section.split('\n')
  const bodyStart = lines.findIndex((line) => SOURCES_HEADING_PATTERN.test(line.trim()))
  if (bodyStart === -1) return []

  return lines
    .slice(bodyStart + 1)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !/^#{1,3}\s/.test(line))
}

function lineIndicatesExternalSource(line: string): boolean {
  return (
    EXTERNAL_SOURCE_INDICATORS.some((pattern) => pattern.test(line)) ||
    DOCUMENT_FILENAME_PATTERN.test(line) ||
    /^\[\d+\]\s+\S+/.test(line)
  )
}

function lineIndicatesGeneralKnowledge(line: string): boolean {
  return GENERAL_KNOWLEDGE_INDICATORS.some((pattern) => pattern.test(line))
}

/**
 * Returns true when the Sources section should be visible (external/user-provided
 * sources were used). Returns false for general-knowledge-only responses.
 */
export function shouldShowSourcesSection(
  content: string,
  options: SourceDisplayOptions = {},
): boolean {
  if (options.webSearchUsed || options.documentsUsed) {
    return true
  }

  const start = findSourcesSectionStart(content)
  if (start === null) {
    return false
  }

  const section = content.slice(start)
  const bodyLines = sectionBodyLines(section)
  if (bodyLines.length === 0) {
    return false
  }

  const hasExternal = bodyLines.some(lineIndicatesExternalSource)
  if (hasExternal) {
    return true
  }

  const hasGeneralKnowledge = bodyLines.some(lineIndicatesGeneralKnowledge)
  if (hasGeneralKnowledge && !hasExternal) {
    return false
  }

  // Unknown source lines default to visible for transparency.
  return bodyLines.some((line) => !lineIndicatesGeneralKnowledge(line))
}

/**
 * Removes the Sources Used section from content when it should not be displayed.
 */
export function prepareContentForDisplay(
  content: string,
  options: SourceDisplayOptions = {},
): string {
  if (!content || shouldShowSourcesSection(content, options)) {
    return content
  }

  const start = findSourcesSectionStart(content)
  if (start === null) {
    return content
  }

  return content.slice(0, start).replace(/\s+$/, '')
}
