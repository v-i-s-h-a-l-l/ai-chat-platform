/**
 * Content Normalization Pipeline
 *
 * Transforms AI-generated responses into clean, renderable Markdown.
 * Handles mixed HTML/Markdown, inconsistent formatting, malformed tables,
 * and other imperfect LLM output.
 *
 * Pipeline order matters:
 *   1. Protect fenced code blocks (never touch their contents)
 *   2. Convert HTML → Markdown
 *   3. Strip unsafe HTML tags (content preserved)
 *   4. Convert oversized/list-heavy tables → headings + lists
 *   5. Normalize bullets + whitespace (NON-table lines only)
 *   6. Repair malformed markdown tables (validate → repair → blank-line guard)
 *   7. Fix list spacing
 *   8. Restore code blocks
 */

import { repairMarkdownTables } from './markdownTableRepair'
import { formatChatResponse } from './chatResponseFormatter'

const CODE_FENCE_PLACEHOLDER = '\u0000CODE_FENCE_'

/** Extract fenced code blocks and replace them with placeholders. */
function protectCodeBlocks(content: string): { text: string; blocks: string[] } {
  const blocks: string[] = []
  const text = content.replace(/```[\s\S]*?```/g, (match) => {
    const idx = blocks.length
    blocks.push(match)
    return `${CODE_FENCE_PLACEHOLDER}${idx}\u0000`
  })
  return { text, blocks }
}

/** Restore fenced code blocks from placeholders. */
function restoreCodeBlocks(content: string, blocks: string[]): string {
  return content.replace(
    new RegExp(`${CODE_FENCE_PLACEHOLDER}(\\d+)\\u0000`, 'g'),
    (_, idx) => blocks[Number(idx)] ?? '',
  )
}

/** A line is (part of) a markdown table if it contains a pipe. */
function isTableLine(line: string): boolean {
  return line.includes('|')
}

/**
 * Normalize AI-generated content before rendering.
 */
export function normalizeAIContent(content: string): string {
  if (!content || typeof content !== 'string') {
    return ''
  }

  // Step 0: Protect code blocks so nothing below mangles their contents
  const { text: protectedText, blocks } = protectCodeBlocks(content)
  let normalized = protectedText

  // Step 1: Convert all HTML break variants → double newline (paragraph break)
  normalized = normalized.replace(/<br\s*\/?>/gi, '\n')

  // Step 2: Convert common inline HTML formatting → Markdown
  normalized = normalized
    .replace(/<b>(.*?)<\/b>/gi, '**$1**')
    .replace(/<strong>(.*?)<\/strong>/gi, '**$1**')
    .replace(/<i>(.*?)<\/i>/gi, '*$1*')
    .replace(/<em>(.*?)<\/em>/gi, '*$1*')
    .replace(/<code>(.*?)<\/code>/gi, '`$1`')

  // Step 3: Remove any remaining unsupported HTML tags (keep inner content).
  // Structural markdown-relevant tags are preserved for the parser.
  normalized = normalized.replace(
    /<\/?(?!br|b|strong|i|em|code|pre|table|tr|td|th|thead|tbody|ul|ol|li|a|img|h[1-6])[^>]+>/gi,
    '',
  )

  // Step 4: Convert chat-unfriendly tables (lists/long cells) into sections
  normalized = formatChatResponse(normalized)

  // Step 5: Per-line normalization. CRITICAL: skip table lines so we never
  // mangle pipe structure (the old global pipe-replace broke tables).
  normalized = normalized
    .split('\n')
    .map((line) => {
      if (isTableLine(line)) {
        // Leave table pipe structure intact; repair engine handles it.
        return line.replace(/\s+$/g, '')
      }
      // Normalize unicode bullets → "- "
      let out = line.replace(/^(\s*)[\u2022\u2023\u25E6\u2043\u2219]\s+/, '$1- ')
      // Collapse runs of spaces/tabs (not newlines) to a single space
      out = out.replace(/[^\S\n]{2,}/g, ' ')
      // Trim trailing whitespace
      out = out.replace(/\s+$/g, '')
      return out
    })
    .join('\n')

  // Step 6: Collapse 3+ blank lines → one blank line
  normalized = normalized.replace(/\n{3,}/g, '\n\n')

  // Step 7: Validate + repair malformed markdown tables. This also guarantees
  normalized = repairMarkdownTables(normalized)

  // Step 8: Ensure proper spacing around list blocks
  normalized = fixListFormatting(normalized)

  // Step 9: Restore code blocks
  normalized = restoreCodeBlocks(normalized, blocks)

  // Step 10: Final trim
  normalized = normalized.trim()

  return normalized
}

/**
 * Fix list formatting: ensure a blank line before/after list blocks so the
 * parser renders them as real lists (not loose paragraphs).
 */
function fixListFormatting(content: string): string {
  const lines = content.split('\n')
  const result: string[] = []
  let inList = false
  let prevLineEmpty = true

  const isListItem = (line: string) => /^(\s*)([-*+]|\d+\.)\s/.test(line)

  for (const line of lines) {
    const listItem = isListItem(line)
    const isEmpty = line.trim() === ''
    const isTable = isTableLine(line)

    if (listItem && !isTable) {
      if (!inList && result.length > 0 && !prevLineEmpty) {
        result.push('')
      }
      inList = true
      result.push(line)
    } else if (inList && !isEmpty && !listItem) {
      if (!prevLineEmpty) result.push('')
      inList = false
      result.push(line)
    } else {
      if (isEmpty) inList = false
      result.push(line)
    }

    prevLineEmpty = isEmpty
  }

  return result.join('\n')
}

/**
 * Memoization cache for normalized content.
 * Avoids re-processing identical content (e.g. across re-renders).
 */
const normalizationCache = new Map<string, string>()
const MAX_CACHE_SIZE = 100

export function normalizeAIContentMemo(content: string): string {
  if (normalizationCache.has(content)) {
    return normalizationCache.get(content)!
  }

  const normalized = normalizeAIContent(content)

  if (normalizationCache.size >= MAX_CACHE_SIZE) {
    const firstKey = normalizationCache.keys().next().value
    if (firstKey !== undefined) normalizationCache.delete(firstKey)
  }

  normalizationCache.set(content, normalized)
  return normalized
}
