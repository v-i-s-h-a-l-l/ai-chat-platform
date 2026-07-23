# Chat Layout and Responsive Content

Assistant responses use a documentation-oriented layout while user messages retain a compact conversational shape.

## Width strategy

- The message feed is centered in a `1280px` container.
- Assistant responses may use up to `1200px` or 92% of available width.
- User messages remain capped near `680px`.
- The composer follows the wider feed alignment.

This keeps short conversations familiar while allowing tables, legal text, research material, and document answers to use available desktop space.

## Responsive behavior

- Desktop responses use the full documentation width.
- Tablet table typography and padding are reduced.
- Mobile tables remain in horizontal overflow containers.
- Long URLs, titles, code, and unbroken words wrap without widening the page.

## Table presentation

Markdown tables render with:

- consistent cell padding and borders
- top-aligned wrapped content
- alternating row backgrounds
- sticky headers where the containing scroll context permits
- responsive horizontal scrolling
- safe card fallback for unrecoverable malformed table output

## Related files

- `frontend/src/components/chat/ChatWindow.tsx`
- `frontend/src/components/chat/MessageBubble.tsx`
- `frontend/src/components/chat/MarkdownContent.tsx`
- `frontend/src/styles/markdown.css`
