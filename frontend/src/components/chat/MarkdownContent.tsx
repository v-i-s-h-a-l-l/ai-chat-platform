import {
  Children,
  isValidElement,
  memo,
  useMemo,
  createElement,
  type ReactNode,
} from 'react'
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
import {
  prepareContentForDisplay,
  type SourceDisplayOptions,
} from '../../utils/sourceSectionDisplay'
import { installRenderTelemetry } from '../../utils/renderTelemetry'
import { SafeTable, looksLikeRawTable } from './SafeTable'
import {
  extractNodeText,
  NumberedSectionHeading,
  NumberedSectionRow,
  parseNumberedHeading,
  SectionNumberBadge,
  shouldRenderAsSectionBadge,
} from './NumberedSectionHeading'
import { isDigitSequence, toPlainDigitSequence, coalesceSectionNumber } from '../../utils/plainTextDigits'

// Install markdown-repair telemetry once at module load.
installRenderTelemetry()

interface MarkdownContentProps {
  content: string
  sourceDisplay?: SourceDisplayOptions
}

function extractText(node: ReactNode): string {
  return extractNodeText(node)
}

function tryParseFlexSectionRow(
  children: ReactNode,
): { number: string; title: ReactNode } | null {
  const items = Children.toArray(children)
  if (items.length < 2) return null

  const first = items[0]
  if (!isValidElement(first)) return null

  const firstProps = first.props as { className?: string; children?: ReactNode }
  const badgeText = extractText(first).trim()
  if (!isDigitSequence(badgeText)) return null

  const second = items[1]
  const secondIsHeading =
    isValidElement(second) &&
    typeof second.type === 'string' &&
    /^h[1-6]$/.test(second.type)

  const isBadge =
    shouldRenderAsSectionBadge(firstProps.className, firstProps.children) ||
    secondIsHeading

  if (!isBadge) return null

  const titleParts = items.slice(1)
  const titleText = extractText(titleParts.length === 1 ? titleParts[0] : titleParts)
  const coalesced = coalesceSectionNumber(badgeText, titleText)
  return { number: coalesced.number, title: coalesced.title }
}

function createHeadingRenderer(level: 1 | 2 | 3 | 4 | 5 | 6) {
  return function HeadingRenderer({ children }: { children?: ReactNode }) {
    const text = extractText(children)
    const parsed = parseNumberedHeading(text)

    if (parsed) {
      return (
        <NumberedSectionHeading level={level} number={parsed.number} title={parsed.title} />
      )
    }

    return createElement(`h${level}`, null, children)
  }
}

const headingComponents = {
  h1: createHeadingRenderer(1),
  h2: createHeadingRenderer(2),
  h3: createHeadingRenderer(3),
  h4: createHeadingRenderer(4),
  h5: createHeadingRenderer(5),
  h6: createHeadingRenderer(6),
}

function renderSectionBadge(children: ReactNode) {
  return <SectionNumberBadge number={toPlainDigitSequence(extractText(children))} />
}

function renderFlexSectionRow(
  as: 'div' | 'p',
  className: string | undefined,
  children: ReactNode,
  props: Record<string, unknown>,
) {
  const parsed = tryParseFlexSectionRow(children)
  if (parsed) {
    return <NumberedSectionRow as={as} number={parsed.number} title={parsed.title} />
  }

  return createElement(as, { className, ...props }, children)
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
    // Allow className for code syntax highlighting and section badges
    code: [...(defaultSchema.attributes?.code || []), 'className'],
    span: [...(defaultSchema.attributes?.span || []), 'className'],
    div: [...(defaultSchema.attributes?.div || []), 'className'],
    p: [...(defaultSchema.attributes?.p || []), 'className'],
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

export const MarkdownContent = memo(function MarkdownContent({
  content,
  sourceDisplay,
}: MarkdownContentProps) {
  const displayContent = useMemo(
    () => prepareContentForDisplay(content, sourceDisplay),
    [content, sourceDisplay?.documentsUsed, sourceDisplay?.webSearchUsed],
  )

  // Normalize content once and memoize the result
  const normalizedContent = useMemo(
    () => normalizeAIContentMemo(displayContent),
    [displayContent],
  )

  return (
    <div className="chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[
          rehypeRaw, // Parse HTML within Markdown
          [rehypeSanitize, customSanitizeSchema], // Sanitize to prevent XSS
          [rehypeHighlight, { detect: false, subset: HIGHLIGHT_SUBSET }], // Syntax highlighting
        ]}
        components={{
          ...headingComponents,
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
          p({ className, children, ...props }) {
            const text = extractText(children)
            if (looksLikeRawTable(text)) {
              return <SafeTable raw={text} />
            }

            const parsedHeading = parseNumberedHeading(text)
            if (parsedHeading && !className?.includes('flex')) {
              return (
                <NumberedSectionRow
                  as="p"
                  number={parsedHeading.number}
                  title={parsedHeading.title}
                />
              )
            }

            if (className?.includes('flex')) {
              return renderFlexSectionRow('p', className, children, props)
            }

            return (
              <p className={className} {...props}>
                {children}
              </p>
            )
          },
          div({ className, children, ...props }) {
            if (className?.includes('flex')) {
              return renderFlexSectionRow('div', className, children, props)
            }
            return (
              <div className={className} {...props}>
                {children}
              </div>
            )
          },
          span({ className, children, ...props }) {
            if (shouldRenderAsSectionBadge(className, children)) {
              return renderSectionBadge(children)
            }
            return (
              <span className={className} {...props}>
                {children}
              </span>
            )
          },
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  )
})
