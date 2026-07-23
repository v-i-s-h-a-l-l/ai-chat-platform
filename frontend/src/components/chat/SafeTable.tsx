/**
 * SafeTable — last-resort fallback renderer.
 *
 * If raw markdown table syntax ever slips past the repair engine and remark-gfm
 * (so it would otherwise appear as a literal paragraph full of pipes), we detect
 * it here and render a proper HTML table instead. If even that fails, we render
 * the data as responsive cards. The user NEVER sees raw pipe syntax.
 */

import { memo } from 'react'
import { parseMarkdownTable } from '../../utils/markdownTableRepair'

interface SafeTableProps {
  /** Raw text that looks like a markdown table. */
  raw: string
}

/** Heuristic: does this text look like a (possibly broken) markdown table? */
export function looksLikeRawTable(text: string): boolean {
  const lines = text.trim().split('\n')
  if (lines.length < 2) return false
  const pipeLines = lines.filter((l) => l.includes('|'))
  // At least 2 pipe-containing lines and a dashed separator somewhere
  const hasSeparator = lines.some((l) => /^[\s|:-]+$/.test(l.trim()) && l.includes('-'))
  return pipeLines.length >= 2 && hasSeparator
}

function alignToStyle(align: 'left' | 'right' | 'center' | 'none'): React.CSSProperties {
  if (align === 'none') return {}
  return { textAlign: align }
}

export const SafeTable = memo(function SafeTable({ raw }: SafeTableProps) {
  const parsed = parseMarkdownTable(raw)

  // Fallback 1: couldn't parse → render as responsive cards
  if (!parsed || parsed.headers.length === 0) {
    return <FallbackCards raw={raw} />
  }

  const { headers, rows, alignments } = parsed

  return (
    <div style={{ overflowX: 'auto', marginTop: '1rem', marginBottom: '1rem' }}>
      <table>
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} style={alignToStyle(alignments[i] ?? 'none')}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) => (
                <td key={c} style={alignToStyle(alignments[c] ?? 'none')}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
})

/** Fallback 2: render key/value-ish content as cards when table parsing fails. */
const FallbackCards = memo(function FallbackCards({ raw }: SafeTableProps) {
  const rows = raw
    .trim()
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.includes('|') && !/^[\s|:-]+$/.test(line))
    .map((line) =>
      line
        .replace(/^\|/, '')
        .replace(/\|$/, '')
        .split('|')
        .map((c) => c.trim()),
    )

  if (rows.length === 0) {
    return <p className="whitespace-pre-wrap">{raw}</p>
  }

  return (
    <div className="safe-cards">
      {rows.map((cells, i) => (
        <div key={i} className="safe-card">
          {cells.map((cell, j) => (
            <div key={j} className="safe-card-cell">
              {cell}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
})
