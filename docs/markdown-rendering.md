# AI Response Rendering

The frontend renders assistant responses through a defensive Markdown pipeline designed for imperfect model output.

## Pipeline

```text
AI response
  -> normalize HTML breaks and whitespace
  -> detect and repair malformed Markdown tables
  -> parse GitHub-Flavored Markdown
  -> parse allowed embedded HTML
  -> sanitize the HTML tree
  -> syntax-highlight code
  -> render responsive React components
```

## Main files

- `frontend/src/utils/contentNormalizer.ts`: protects code fences, converts common HTML formatting, normalizes lists, and invokes table repair.
- `frontend/src/utils/markdownTableRepair.ts`: repairs missing separators, duplicate pipes, and inconsistent column counts.
- `frontend/src/components/chat/MarkdownContent.tsx`: configures `react-markdown`, `remark-gfm`, `rehype-raw`, `rehype-sanitize`, and code highlighting.
- `frontend/src/components/chat/SafeTable.tsx`: final table/card fallback when malformed table syntax reaches the renderer.
- `frontend/src/styles/markdown.css`: typography, lists, tables, code, blockquotes, links, and mobile behavior.

## Security

Arbitrary HTML is not inserted with `dangerouslySetInnerHTML`. Embedded HTML passes through `rehype-sanitize`, which removes unsupported tags, dangerous attributes, event handlers, and unsafe URL protocols.

## Performance

Completed assistant messages use a memoized normalization cache, memoized React components, and lazy loading for the Markdown/highlighting stack. Streaming text remains a lightweight plain-text render until completion.

## Tables

Tables use native HTML table layout inside an overflow container. Cells are top-aligned and wrap long content; narrow screens scroll horizontally rather than expanding the page.
