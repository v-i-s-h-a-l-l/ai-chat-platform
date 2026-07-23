import { lazy, memo, Suspense } from 'react'
import { SparklesIcon } from '../icons/NavIcons'
import { TypingIndicator } from './TypingIndicator'

// Code-split the markdown/syntax-highlighting stack (react-markdown, remark-gfm,
// rehype-highlight, highlight.js) — it's only needed once a message finishes
// streaming, not for the initial app shell.
const MarkdownContent = lazy(() =>
  import('./MarkdownContent').then((m) => ({ default: m.MarkdownContent })),
)

interface MessageBubbleProps {
  role: 'user' | 'assistant'
  content: string
  webSearchUsed?: boolean
  isStreaming?: boolean
}

export const MessageBubble = memo(function MessageBubble({
  role,
  content,
  webSearchUsed,
  isStreaming,
}: MessageBubbleProps) {
  const isUser = role === 'user'

  return (
    <div className={`animate-fade-in flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl text-xs font-bold ${
          isUser
            ? 'bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-sm shadow-violet-500/30'
            : 'border border-zinc-200 bg-white text-violet-600 shadow-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-violet-400'
        }`}
      >
        {isUser ? (
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        ) : (
          <SparklesIcon className="h-3.5 w-3.5" />
        )}
      </div>

      <div className={`${isUser ? 'max-w-[min(680px,85%)]' : 'max-w-[min(1200px,92%)] w-full'} ${isUser ? '' : 'space-y-2'}`}>
        {!isUser && webSearchUsed && (
          <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[11px] font-medium text-sky-700 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-300">
            🌐 Web Search Used
          </span>
        )}
        <div
          className={`${
            isUser
              ? 'rounded-2xl rounded-tr-md bg-gradient-to-br from-violet-600 to-violet-700 px-4 py-3 text-white shadow-md shadow-violet-600/15'
              : 'rounded-2xl rounded-tl-md border border-zinc-200/80 bg-white px-6 py-4 shadow-sm dark:border-zinc-700/80 dark:bg-zinc-900'
          }`}
        >
          {isUser ? (
            <p className="text-[0.9375rem] leading-relaxed whitespace-pre-wrap">{content}</p>
          ) : isStreaming && !content ? (
            <TypingIndicator />
          ) : isStreaming ? (
            <p className="text-[0.9375rem] leading-relaxed whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
              {content}
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-violet-500 align-middle" />
            </p>
          ) : (
            <Suspense
              fallback={
                <p className="text-[0.9375rem] leading-relaxed whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
                  {content}
                </p>
              }
            >
              <MarkdownContent content={content} />
            </Suspense>
          )}
        </div>
      </div>
    </div>
  )
})
