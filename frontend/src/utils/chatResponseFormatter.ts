/**
 * Chat Response Formatter
 *
 * Mirrors the backend response_formatter.py safety net: converts tables with
 * oversized cells or nested lists into headings + lists before table repair.
 */

const MAX_CELL_LINES = 3
const MAX_CELL_CHARS = 150
const LIST_ITEM_RE = /^\s*(?:[-*+]|(?:\d+\.))\s/m
const SEPARATOR_ROW_RE = /^\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?$/

function looksLikeTableRow(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed || trimmed.startsWith('```')) return false
  return trimmed.includes('|')
}

function isSeparatorRow(line: string): boolean {
  const trimmed = line.trim().replace(/\|{2,}/g, '|')
  if (!trimmed.includes('-')) return false
  return SEPARATOR_ROW_RE.test(trimmed)
}

function splitCells(line: string): string[] {
  let trimmed = line.trim().replace(/\|{2,}/g, '|')
  if (trimmed.startsWith('|')) trimmed = trimmed.slice(1)
  if (trimmed.endsWith('|')) trimmed = trimmed.slice(0, -1)

  const cells: string[] = []
  let current = ''
  for (let i = 0; i < trimmed.length; i++) {
    const ch = trimmed[i]
    if (ch === '\\' && i + 1 < trimmed.length) {
      current += trimmed.slice(i, i + 2)
      i++
      continue
    }
    if (ch === '|') {
      cells.push(current.trim())
      current = ''
      continue
    }
    current += ch
  }
  cells.push(current.trim())
  return cells
}

function cellViolates(cell: string): boolean {
  const stripped = cell.trim()
  if (!stripped) return false
  if (stripped.length > MAX_CELL_CHARS) return true
  if (stripped.includes('\n\n')) return true
  const lines = stripped.split('\n').filter((l) => l.trim())
  if (lines.length > MAX_CELL_LINES) return true
  if (LIST_ITEM_RE.test(stripped)) return true
  return false
}

function formatCellContent(cell: string): string {
  const stripped = cell.trim()
  if (!stripped) return ''
  const lines = stripped.split('\n').map((l) => l.trim()).filter(Boolean)
  if (lines.length > 0 && lines.every((l) => LIST_ITEM_RE.test(l))) {
    return lines.join('\n')
  }
  return stripped.replace(/\n\n/g, '\n')
}

function convertTableToSections(header: string[], rows: string[][]): string {
  const sections: string[] = []

  if (header.length === 1) {
    sections.push(`## ${header[0]}\n`)
    for (const row of rows) {
      sections.push(formatCellContent(row[0] ?? ''))
      sections.push('')
    }
    return sections.join('\n').trim()
  }

  if (header.length === 2) {
    for (const row of rows) {
      const title = row[0] ?? 'Item'
      const body = row[1] ?? ''
      sections.push(`## ${title}\n`)
      const formatted = formatCellContent(body)
      if (formatted) sections.push(formatted)
      sections.push('\n---\n')
    }
    return sections.join('\n').trim().replace(/\n---\s*$/, '').trim()
  }

  sections.push('## Details\n')
  rows.forEach((row, idx) => {
    const title = row[0]?.trim() || `Item ${idx + 1}`
    sections.push(`### ${title}\n`)
    for (let col = 1; col < header.length; col++) {
      const value = row[col] ?? ''
      if (!value.trim()) continue
      sections.push(`**${header[col]}**\n`)
      sections.push(formatCellContent(value))
      sections.push('')
    }
    sections.push('---\n')
  })
  return sections.join('\n').trim().replace(/\n---\s*$/, '').trim()
}

function parseTableBlock(blockLines: string[]): { header: string[]; rows: string[][] } | null {
  const nonEmpty = blockLines.filter((l) => l.trim())
  if (nonEmpty.length < 2) return null

  const header = splitCells(nonEmpty[0])
  if (!header.length || header.every((c) => !c)) return null

  let dataStart = 1
  if (nonEmpty.length > 1 && isSeparatorRow(nonEmpty[1])) dataStart = 2

  const rows: string[][] = []
  for (const line of nonEmpty.slice(dataStart)) {
    if (isSeparatorRow(line)) continue

    const stripped = line.trim()
    if (stripped.startsWith('|')) {
      rows.push(splitCells(line))
      continue
    }

    if (rows.length) {
      const continuation = stripped.replace(/\|$/, '').trim()
      const lastRow = rows[rows.length - 1]
      lastRow[lastRow.length - 1] = `${lastRow[lastRow.length - 1]}\n${continuation}`.trim()
      continue
    }

    rows.push(splitCells(line))
  }

  const filtered = rows.filter((row) => row.some((cell) => cell.trim()))
  if (!filtered.length) return null
  return { header, rows: filtered }
}

function tableNeedsConversion(header: string[], rows: string[][]): boolean {
  for (const cell of header) {
    if (cellViolates(cell)) return true
  }
  for (const row of rows) {
    for (const cell of row) {
      if (cellViolates(cell)) return true
    }
  }

  if (header.length >= 3) {
    for (const row of rows) {
      for (const cell of row) {
        if (cell.trim().length > 80) return true
      }
    }
  }

  return false
}

function findTableBlockEnd(lines: string[], start: number): number | null {
  if (!looksLikeTableRow(lines[start])) return null

  let end = start + 1
  while (end < lines.length) {
    const line = lines[end]
    if (!line.trim()) break
    if (looksLikeTableRow(line) || isSeparatorRow(line)) {
      end++
      continue
    }
    if (end > start + 1) {
      end++
      continue
    }
    break
  }
  return end - start >= 2 ? end : null
}

/**
 * Convert problematic markdown tables into chat-friendly headings and lists.
 */
export function formatChatResponse(content: string): string {
  if (!content?.trim()) return content

  const lines = content.split('\n')
  const output: string[] = []
  let i = 0

  while (i < lines.length) {
    const blockEnd = findTableBlockEnd(lines, i)
    if (blockEnd === null) {
      output.push(lines[i])
      i++
      continue
    }

    const blockLines = lines.slice(i, blockEnd)
    const parsed = parseTableBlock(blockLines)

    if (parsed && tableNeedsConversion(parsed.header, parsed.rows)) {
      if (output.length && output[output.length - 1].trim()) output.push('')
      output.push(convertTableToSections(parsed.header, parsed.rows))
      if (blockEnd < lines.length && lines[blockEnd].trim()) output.push('')
    } else {
      output.push(...blockLines)
    }

    i = blockEnd
  }

  return output.join('\n')
}
