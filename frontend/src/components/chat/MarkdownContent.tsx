import { isValidElement, memo, useMemo, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.min.css'
import '../../styles/markdown.css'
import { CodeBlock } from './CodeBlock'
import { HIGHLIGHT_SUBSET } from './codeLanguages'
import { normalizeAIContentMemo } from '../../utils/contentNormalizer'
import { installRenderTelemetry } from '../../utils/renderTelemetry'
import { SafeTable, looksLikeRawTable } from './SafeTable'

// Install markdown-repair telemetry once at module load.
installRenderTelemetry()

interface MarkdownContentProps {
  content: string
}

function extractText(node: ReactNode): string {
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractText).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) {
    return extractText(node.props.children)
  }
  return ''
}

/**
 * Custom sanitization schema.
 * Allows safe HTML tags while preventing XSS.
 * Based on GitHub Flavored Markdown sanitization rules.
 */
const customSanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    // Allow className for code syntax highlighting
    code: [...(defaultSchema.attributes?.code || []), 'className'],
    span: [...(defaultSchema.attributes?.span || []), 'className'],
    div: [...(defaultSchema.attributes?.div || []), 'className'],
  },
  tagNames: [
    ...(defaultSchema.tagNames || []),
    // Ensure table tags are allowed
    'table',
    'thead',
    'tbody',
    'tr',
    'th',
    'td',
  ],
}

export const MarkdownContent = memo(function MarkdownContent({ content }: MarkdownContentProps) {
  // Normalize content once and memoize the result
  const normalizedContent = useMemo(() => normalizeAIContentMemo(content), [content])

  return (
    <div className="chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[
          rehypeRaw, // Parse HTML within Markdown
          [rehypeSanitize, customSanitizeSchema], // Sanitize to prevent XSS
          [rehypeHighlight, { detect: true, subset: HIGHLIGHT_SUBSET }], // Syntax highlighting
        ]}
        components={{
          // Custom code block rendering
          pre({ children }) {
            if (isValidElement(children)) {
              const childProps = children.props as {
                className?: string
                children?: ReactNode
              }
              const className = childProps.className ?? ''
              const match = /language-([\w-]+)/.exec(className)
              const code = extractText(childProps.children).replace(/\n$/, '')
              if (code) {
                return <CodeBlock code={code} language={match?.[1]} />
              }
            }
            return <pre>{children}</pre>
          },
          // Custom inline code rendering
          code({ className, children, ...props }) {
            const isBlock = className?.includes('language-')
            if (isBlock) {
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              )
            }
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            )
          },
          // Ensure tables have proper wrapper for horizontal scroll
          table({ children, ...props }) {
            return (
              <div style={{ overflowX: 'auto', marginTop: '1rem', marginBottom: '1rem' }}>
                <table {...props}>{children}</table>
              </div>
            )
          },
          // Last-resort fallback: if raw table syntax slipped through and was
          // rendered as a plain paragraph, detect it and render a real table.
          p({ children }) {
            const text = extractText(children)
            if (looksLikeRawTable(text)) {
              return <SafeTable raw={text} />
            }
            return <p>{children}</p>
          },
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  )
})
