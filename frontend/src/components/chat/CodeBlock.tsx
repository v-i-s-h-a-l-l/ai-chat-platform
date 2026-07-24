import { memo, useMemo, useState } from 'react'
import { CheckIcon, CopyIcon } from '../icons/NavIcons'
import { getLanguageLabel, highlightCode, resolveCodeLanguage } from './codeLanguages'

interface CodeBlockProps {
  code: string
  language?: string
}

function normalizeCode(code: string): string {
  return code.replace(/\n$/, '')
}

function countLines(code: string): number {
  const normalized = normalizeCode(code)
  if (!normalized) return 1
  return normalized.split('\n').length
}

export const CodeBlock = memo(function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const resolvedLanguage = resolveCodeLanguage(language)
  const label = getLanguageLabel(language)
  const normalizedCode = useMemo(() => normalizeCode(code), [code])

  const highlighted = useMemo(
    () => highlightCode(normalizedCode, resolvedLanguage),
    [normalizedCode, resolvedLanguage],
  )

  const lineNumbers = useMemo(
    () => Array.from({ length: countLines(normalizedCode) }, (_, index) => index + 1),
    [normalizedCode],
  )

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <div className="code-block group my-2 overflow-hidden rounded-lg border border-[#30363d] bg-[#0d1117]">
      <div className="code-block-header flex items-center justify-between border-b border-[#30363d] bg-[#161b22] px-3 py-1.5">
        <span className="code-block-lang font-mono text-[11px] font-medium uppercase tracking-wide text-[#8b949e]">
          {label}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={copied ? 'Copied' : 'Copy code'}
          className="code-block-copy flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium text-[#8b949e] transition hover:bg-[#21262d] hover:text-[#e6edf3]"
        >
          {copied ? (
            <>
              <CheckIcon className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <CopyIcon className="h-3.5 w-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <div className="code-block-scroll overflow-x-auto">
        <div className="code-block-body">
          <div className="code-block-gutters" aria-hidden="true">
            {lineNumbers.map((number) => (
              <div key={number} className="code-block-gutter-line">
                {number}
              </div>
            ))}
          </div>
          <pre className="code-block-pre">
            <code className="hljs" dangerouslySetInnerHTML={{ __html: highlighted }} />
          </pre>
        </div>
      </div>
    </div>
  )
})
