/**
 * Plain-text digit normalization for the chat rendering layer.
 *
 * LLM output sometimes contains Unicode keycap sequences (e.g. 1️⃣, 0️⃣) where
 * ASCII digits are expected. Keycaps also break `\d+` parsing — "1️⃣0. Title"
 * matches only "1" and leaves "0️⃣…" in the title, producing "1 0️⃣".
 *
 * These helpers are used only at render time; stored markdown is not modified.
 */

/** ASCII digit + optional VS16 + combining enclosing keycap (U+20E3). */
const KEYCAP_DIGIT_RE = /(\d)\uFE0F?\u20E3/g

/** Stray combining keycap marks left after partial normalization. */
const LONE_KEYCAP_MARK_RE = /\uFE0F?\u20E3/g

/** Leading section index: digits with optional keycap emoji after each digit. */
const LEADING_SECTION_NUMBER_RE = /^((?:\d(?:\uFE0F?\u20E3)?)+)\.?\s+(.+)$/u

/** Convert keycap emoji digits back to plain ASCII digits (number tokens only). */
export function normalizeKeycapDigits(text: string): string {
  return text
    .replace(KEYCAP_DIGIT_RE, (_match, digit: string) => digit)
    .replace(LONE_KEYCAP_MARK_RE, '')
}

/** True when text is a plain or keycap-encoded digit sequence (e.g. "10", "1️⃣0"). */
export function isDigitSequence(text: string): boolean {
  const normalized = normalizeKeycapDigits(text.trim())
  return /^\d+$/.test(normalized)
}

/** Render-safe plain digit string for badges and section numbers. */
export function toPlainDigitSequence(text: string): string {
  return normalizeKeycapDigits(text.trim())
}

/**
 * Recover multi-digit section numbers split across badge + title
 * (e.g. number "1" + title "0️⃣ Conclusion" → "10", "Conclusion").
 */
export function coalesceSectionNumber(
  number: string,
  title: string,
): { number: string; title: string } {
  let plainNumber = toPlainDigitSequence(number)
  const plainTitle = title.trim()

  if (plainNumber.length !== 1 || !plainTitle) {
    return { number: plainNumber, title: plainTitle }
  }

  const keycapLead = /^(\d)\uFE0F?\u20E3[\.\s]?\s*(.*)$/.exec(plainTitle)
  if (keycapLead) {
    return {
      number: plainNumber + keycapLead[1],
      title: keycapLead[2].trim(),
    }
  }

  const dotLead = /^(\d)\.\s+(.*)$/.exec(plainTitle)
  if (dotLead && dotLead[1] !== plainNumber) {
    return {
      number: plainNumber + dotLead[1],
      title: dotLead[2].trim(),
    }
  }

  return { number: plainNumber, title: plainTitle }
}

/** Parse a numbered section heading while preserving emoji in the title text. */
export function parseLeadingSectionNumber(
  text: string,
): { number: string; title: string } | null {
  const trimmed = text.trim()
  if (!trimmed) return null

  const match = LEADING_SECTION_NUMBER_RE.exec(trimmed)
  if (!match) return null

  const coalesced = coalesceSectionNumber(toPlainDigitSequence(match[1]), match[2].trim())
  if (!coalesced.title) return null

  return coalesced
}
