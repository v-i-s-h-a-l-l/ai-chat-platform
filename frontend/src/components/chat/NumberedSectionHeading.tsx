import { createElement, type ReactNode } from 'react'
import {
  coalesceSectionNumber,
  isDigitSequence,
  parseLeadingSectionNumber,
  toPlainDigitSequence,
} from '../../utils/plainTextDigits'

export function parseNumberedHeading(text: string): { number: string; title: string } | null {
  return parseLeadingSectionNumber(text)
}

/** True when node text is only digits (section index badge). */
export function isNumericBadgeText(node: ReactNode): boolean {
  return isDigitSequence(extractNodeText(node))
}

export function extractNodeText(node: ReactNode): string {
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractNodeText).join('')
  if (node && typeof node === 'object' && 'props' in node) {
    const props = (node as { props?: { children?: ReactNode } }).props
    return extractNodeText(props?.children)
  }
  return ''
}

/** Detect Tailwind / inline fixed-size badge boxes that wrap multi-digit numbers. */
export function hasFixedBadgeBoxClass(className?: string): boolean {
  if (!className) return false
  if (className.includes('section-number-badge')) return true
  if (/\bsize-[567]\b/.test(className)) return true
  return /\bh-[567]\b/.test(className) && /\bw-[567]\b/.test(className)
}

export function shouldRenderAsSectionBadge(
  className: string | undefined,
  children: ReactNode,
): boolean {
  if (!isNumericBadgeText(children)) return false
  return hasFixedBadgeBoxClass(className)
}

export function SectionNumberBadge({ number }: { number: string }) {
  return (
    <span className="section-number-badge">{toPlainDigitSequence(number)}</span>
  )
}

interface NumberedSectionHeadingProps {
  level: 1 | 2 | 3 | 4 | 5 | 6
  number: string
  title: ReactNode
}

export function NumberedSectionHeading({ level, number, title }: NumberedSectionHeadingProps) {
  return createElement(
    `h${level}`,
    { className: 'section-heading-numbered' },
    createElement(SectionNumberBadge, { number }),
    createElement('span', { className: 'section-heading-title' }, title),
  )
}

interface NumberedSectionRowProps {
  number: string
  title: ReactNode
  as?: 'div' | 'p'
}

/** Flex row used when LLM emits HTML badge + title instead of a markdown heading. */
export function NumberedSectionRow({ number, title, as = 'div' }: NumberedSectionRowProps) {
  const titleText =
    typeof title === 'string' ? title : extractNodeText(title).trim()
  const coalesced = coalesceSectionNumber(number, titleText)

  return createElement(
    as,
    { className: 'section-heading-numbered' },
    createElement(SectionNumberBadge, { number: coalesced.number }),
    createElement('span', { className: 'section-heading-title' }, coalesced.title),
  )
}
