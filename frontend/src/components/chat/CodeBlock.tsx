import { memo, useMemo, useState } from 'react'
import { CheckIcon, CopyIcon } from '../icons/NavIcons'
import { getLanguageLabel, highlightCode } from './codeLanguages'

interface CodeBlockProps {
  code: string
  language?: string
}

export const CodeBlock = memo(function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const label = getLanguageLabel(language)

  const lines = useMemo(() => {
    const highlighted = highlightCode(code, language)
    return highlighted.split('\n')
  }, [code, language])

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
    <div className="code-block group my-3 overflow-hidden rounded-xl border border-zinc-700/60 bg-[#0d1117] shadow-sm">
      <div className="flex items-center justify-between border-b border-zinc-700/60 bg-[#161b22] px-4 py-2">
        <span className="font-mono text-[12px] font-medium text-zinc-400">{label}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] font-medium text-zinc-400 transition hover:bg-zinc-700/50 hover:text-zinc-200"
        >
          {copied ? (
            <>
              <CheckIcon className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
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
        <table className="code-block-table w-full border-collapse">
          <tbody>
            {lines.map((line, index) => (
              <tr key={index} className="code-block-row">
                <td className="code-block-gutter select-none text-right align-top font-mono text-[12px] leading-6 text-zinc-500">
                  {index + 1}
                </td>
                <td className="code-block-line align-top font-mono text-[13px] leading-6">
                  <code
                    className="hljs block bg-transparent p-0 text-inherit"
                    dangerouslySetInnerHTML={{ __html: line || '&nbsp;' }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
})
