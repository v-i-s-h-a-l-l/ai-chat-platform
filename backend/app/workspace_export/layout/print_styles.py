"""Professional print CSS — used for HTML layout and ReportLab style mapping."""

from __future__ import annotations

PRINT_CSS = """
@page {
  size: letter;
  margin: 0.85in 0.85in 0.9in 0.85in;
}

body {
  font-family: "Vera", "Helvetica", sans-serif;
  font-size: 11pt;
  line-height: 1.55;
  color: #1a1a1a;
}

.doc-title {
  font-size: 22pt;
  font-weight: 700;
  margin: 0 0 12pt 0;
  line-height: 1.25;
}

.doc-meta {
  background: #f8f9fb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10pt 12pt;
  margin: 0 0 18pt 0;
  font-size: 9pt;
  color: #4b5563;
}

.doc-meta dt {
  font-weight: 600;
  display: inline;
}

.doc-meta dd {
  display: inline;
  margin: 0 12pt 0 4pt;
}

h1 { font-size: 18pt; margin: 18pt 0 8pt; font-weight: 700; }
h2 { font-size: 15pt; margin: 16pt 0 7pt; font-weight: 700; }
h3 { font-size: 13pt; margin: 14pt 0 6pt; font-weight: 700; }
h4 { font-size: 11.5pt; margin: 12pt 0 5pt; font-weight: 700; }

p { margin: 0 0 8pt 0; orphans: 3; widows: 3; }

ul, ol { margin: 0 0 10pt 0; padding-left: 18pt; }
li { margin: 0 0 4pt 0; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 12pt 0;
  page-break-inside: avoid;
}

th {
  background: #e8eef7;
  font-weight: 700;
  text-align: left;
  padding: 6pt 8pt;
  border: 0.5pt solid #cbd5e1;
}

td {
  padding: 6pt 8pt;
  border: 0.5pt solid #e2e8f0;
  vertical-align: top;
  word-wrap: break-word;
}

blockquote {
  border-left: 3pt solid #d1d5db;
  margin: 0 0 10pt 0;
  padding: 4pt 0 4pt 12pt;
  color: #374151;
}

pre, code {
  font-family: "VeraMono", "Courier New", monospace;
}

pre {
  background: #f4f4f5;
  border-radius: 6px;
  padding: 10pt 12pt;
  margin: 0 0 10pt 0;
  font-size: 9pt;
  line-height: 1.45;
  page-break-inside: avoid;
}

code {
  background: #f4f4f5;
  padding: 1pt 3pt;
  border-radius: 3px;
  font-size: 9.5pt;
}

hr {
  border: none;
  border-top: 0.5pt solid #d1d5db;
  margin: 14pt 0;
}

a { color: #2563eb; text-decoration: underline; }

.section-group {
  page-break-inside: avoid;
}

.doc-footer {
  font-size: 8pt;
  color: #6b7280;
  font-style: italic;
  margin-top: 16pt;
}
"""

# ReportLab style name mapping from CSS selectors
HEADING_STYLE_MAP = {
    0: "DocTitle",
    1: "Heading1",
    2: "Heading2",
    3: "Heading3",
    4: "Heading4",
    5: "Heading4",
    6: "Heading4",
}
