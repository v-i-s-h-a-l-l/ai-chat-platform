/**
 * Markdown Table Validation & Repair Engine
 *
 * Production AI systems cannot assume LLM output is valid. This module detects
 * malformed GitHub Flavored Markdown tables and repairs them before rendering,
 * so remark-gfm never falls back to rendering a table as plain text.
 *
 * Pipeline: detect blocks → validate → repair → (verify) → telemetry
 *
 * Root cause this solves:
 *   remark-gfm STRICTLY requires the separator row to have the same column
 *   count as the header. A table like:
 *       | A | B | C |
 *       |---|---|          <- 2 cols, header has 3
 *   is rejected entirely and rendered as a literal paragraph with pipes.
 */

export interface TableRepairEvent {
  original: string
  repaired: string
  wasRepaired: boolean
  reason: string
}

type TelemetrySink = (event: TableRepairEvent) => void

let telemetrySink: TelemetrySink | null = null

/** Register a telemetry callback invoked whenever a table is repaired. */
export function setTableRepairTelemetry(sink: TelemetrySink | null): void {
  telemetrySink = sink
}

function emitTelemetry(event: TableRepairEvent): void {
  if (event.wasRepaired && telemetrySink) {
    try {
      telemetrySink(event)
    } catch {
      // Never let telemetry break rendering.
    }
  }
}

/**
 * A line "looks like" part of a table if it contains at least one pipe that
 * isn't purely inside inline code. We keep this permissive on purpose — the
 * validator decides what's actually a table.
 */
function looksLikeTableRow(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed.includes('|')) return false
  // Ignore lines that are clearly not tables (e.g. code fences)
  if (trimmed.startsWith('```')) return false
  return true
}

/** A separator row consists only of pipes, dashes, colons and whitespace. */
function isSeparatorRow(line: string): boolean {
  // Collapse duplicate pipes first so "|-----||" is still recognized.
  const trimmed = line.trim().replace(/\|{2,}/g, '|')
  if (!trimmed.includes('-')) return false
  return /^\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?$/.test(trimmed)
}

/**
 * Split a markdown table row into trimmed cell values.
 * Handles escaped pipes (\|) and collapses duplicate pipes (|| → single split).
 */
function splitCells(line: string): string[] {
  let trimmed = line.trim()
  // Collapse duplicate pipes: "|| Police ||" → "| Police |"
  trimmed = trimmed.replace(/\|{2,}/g, '|')
  // Strip a single leading/trailing pipe so we don't get empty edge cells
  if (trimmed.startsWith('|')) trimmed = trimmed.slice(1)
  if (trimmed.endsWith('|')) trimmed = trimmed.slice(0, -1)

  // Split on unescaped pipes
  const cells: string[] = []
  let current = ''
  for (let i = 0; i < trimmed.length; i++) {
    const ch = trimmed[i]
    if (ch === '\\' && trimmed[i + 1] === '|') {
      current += '|'
      i++
      continue
    }
    if (ch === '|') {
      cells.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  cells.push(current.trim())
  return cells
}

/** Parse alignment markers from a separator row into per-column alignment. */
function parseAlignments(separatorCells: string[]): Array<'left' | 'right' | 'center' | 'none'> {
  return separatorCells.map((cell) => {
    const c = cell.trim()
    const left = c.startsWith(':')
    const right = c.endsWith(':')
    if (left && right) return 'center'
    if (right) return 'right'
    if (left) return 'left'
    return 'none'
  })
}

function buildSeparator(columnCount: number, alignments: Array<'left' | 'right' | 'center' | 'none'>): string {
  const cells: string[] = []
  for (let i = 0; i < columnCount; i++) {
    const align = alignments[i] ?? 'none'
    switch (align) {
      case 'center':
        cells.push(':---:')
        break
      case 'right':
        cells.push('---:')
        break
      case 'left':
        cells.push(':---')
        break
      default:
        cells.push('---')
    }
  }
  return '| ' + cells.join(' | ') + ' |'
}

function buildRow(cells: string[], columnCount: number): string {
  const padded = [...cells]
  while (padded.length < columnCount) padded.push('')
  if (padded.length > columnCount) padded.length = columnCount
  // Escape any stray pipes inside cell content
  const safe = padded.map((c) => c.replace(/\|/g, '\\|'))
  return '| ' + safe.join(' | ') + ' |'
}

interface DetectedTable {
  startLine: number
  endLine: number // exclusive
  lines: string[]
}

/**
 * Scan lines and detect contiguous blocks that are (or look like) tables.
 * A candidate block is 2+ consecutive pipe-containing lines. Code fences are skipped.
 */
function detectTableBlocks(lines: string[]): DetectedTable[] {
  const blocks: DetectedTable[] = []
  let inCodeFence = false
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const fenceMatch = /^\s*```/.test(line)
    if (fenceMatch) {
      inCodeFence = !inCodeFence
      i++
      continue
    }
    if (inCodeFence) {
      i++
      continue
    }

    if (looksLikeTableRow(line)) {
      let j = i + 1
      while (j < lines.length && looksLikeTableRow(lines[j]) && !/^\s*```/.test(lines[j])) {
        j++
      }
      // A table needs at least 2 rows (header + something)
      if (j - i >= 2) {
        blocks.push({ startLine: i, endLine: j, lines: lines.slice(i, j) })
      }
      i = j
    } else {
      i++
    }
  }

  return blocks
}

/**
 * Validate + repair a single detected table block.
 * Returns the repaired markdown lines and whether a change was needed.
 */
function repairTableBlock(block: string[]): { lines: string[]; wasRepaired: boolean; reason: string } {
  const original = block.join('\n')

  // Identify header and separator
  const headerCells = splitCells(block[0])
  const columnCount = headerCells.length

  // Find a separator row (usually line index 1). If missing, synthesize one.
  let separatorIndex = -1
  for (let i = 1; i < block.length; i++) {
    if (isSeparatorRow(block[i])) {
      separatorIndex = i
      break
    }
  }

  let alignments: Array<'left' | 'right' | 'center' | 'none'>
  const bodyRows: string[][] = []
  const reasons: string[] = []

  if (separatorIndex === -1) {
    // No separator row at all — synthesize one right after the header.
    alignments = new Array(columnCount).fill('none')
    reasons.push('missing separator row synthesized')
    for (let i = 1; i < block.length; i++) {
      bodyRows.push(splitCells(block[i]))
    }
  } else {
    const separatorCells = splitCells(block[separatorIndex])
    alignments = parseAlignments(separatorCells)
    if (separatorCells.length !== columnCount) {
      reasons.push(`separator column count (${separatorCells.length}) != header (${columnCount})`)
    }
    // Everything after the separator is a body row. Anything between header and
    // separator (shouldn't happen) is treated as a body row too.
    for (let i = 1; i < block.length; i++) {
      if (i === separatorIndex) continue
      bodyRows.push(splitCells(block[i]))
    }
  }

  // Detect column-count inconsistencies in body rows
  const inconsistent = bodyRows.some((r) => r.length !== columnCount)
  if (inconsistent) reasons.push('inconsistent body column counts normalized')

  // Detect duplicate pipes in the original
  if (/\|\s*\|/.test(original.replace(/^\s*\|/gm, '').replace(/\|\s*$/gm, ''))) {
    // (heuristic — actual duplicate-pipe collapse happens in splitCells)
  }
  if (/\|{2,}/.test(original)) reasons.push('duplicate pipes removed')

  // Rebuild a clean, spec-compliant table
  const rebuilt: string[] = []
  rebuilt.push(buildRow(headerCells, columnCount))
  rebuilt.push(buildSeparator(columnCount, alignments))
  for (const row of bodyRows) {
    rebuilt.push(buildRow(row, columnCount))
  }

  const repairedStr = rebuilt.join('\n')
  const wasRepaired = repairedStr.trim() !== original.trim()

  return {
    lines: rebuilt,
    wasRepaired,
    reason: reasons.join('; ') || (wasRepaired ? 'normalized formatting' : 'valid'),
  }
}

/**
 * Main entry: find all tables in the content, validate + repair each, and
 * guarantee blank lines around them so remark-gfm reliably parses them.
 */
export function repairMarkdownTables(content: string): string {
  if (!content.includes('|')) return content

  const lines = content.split('\n')
  const blocks = detectTableBlocks(lines)
  if (blocks.length === 0) return content

  // Rebuild the document, replacing each detected block with its repaired form.
  const out: string[] = []
  let cursor = 0

  for (const block of blocks) {
    // Push lines before the block
    for (; cursor < block.startLine; cursor++) {
      out.push(lines[cursor])
    }

    const { lines: repairedLines, wasRepaired, reason } = repairTableBlock(block.lines)

    emitTelemetry({
      original: block.lines.join('\n'),
      repaired: repairedLines.join('\n'),
      wasRepaired,
      reason,
    })

    // Guarantee a blank line BEFORE the table (remark-gfm requirement)
    if (out.length > 0 && out[out.length - 1].trim() !== '') {
      out.push('')
    }

    out.push(...repairedLines)

    // Guarantee a blank line AFTER the table
    const nextLine = lines[block.endLine]
    if (nextLine !== undefined && nextLine.trim() !== '') {
      out.push('')
    }

    cursor = block.endLine
  }

  // Push any remaining lines
  for (; cursor < lines.length; cursor++) {
    out.push(lines[cursor])
  }

  return out.join('\n')
}

/**
 * Convert a repaired markdown table block into a structured representation.
 * Used as a last-resort fallback if markdown parsing must be bypassed.
 */
export interface ParsedTable {
  headers: string[]
  rows: string[][]
  alignments: Array<'left' | 'right' | 'center' | 'none'>
}

export function parseMarkdownTable(tableMarkdown: string): ParsedTable | null {
  const lines = tableMarkdown.trim().split('\n').filter((l) => l.trim() !== '')
  if (lines.length < 2) return null

  const headers = splitCells(lines[0])
  const columnCount = headers.length

  let separatorIndex = -1
  for (let i = 1; i < lines.length; i++) {
    if (isSeparatorRow(lines[i])) {
      separatorIndex = i
      break
    }
  }

  const alignments =
    separatorIndex !== -1
      ? parseAlignments(splitCells(lines[separatorIndex]))
      : (new Array(columnCount).fill('none') as Array<'left' | 'right' | 'center' | 'none'>)

  const rows: string[][] = []
  for (let i = 1; i < lines.length; i++) {
    if (i === separatorIndex) continue
    const cells = splitCells(lines[i])
    while (cells.length < columnCount) cells.push('')
    if (cells.length > columnCount) cells.length = columnCount
    rows.push(cells)
  }

  return { headers, rows, alignments }
}
