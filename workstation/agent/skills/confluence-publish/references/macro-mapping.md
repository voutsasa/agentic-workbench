# What the converter can produce

Eleven native macros are reachable: `toc`, `children`, `code`, `status`, `info`, `tip`, `note`,
`warning`, `panel`, `expand` and `anchor`. Four points are worth carrying without opening a template:

- **The admonition keyword is not the panel name, and neither is the macro name.** Three registers,
  all different words, so say which one you mean. This is the whole mapping
  (in `converter.py`) — seventeen keywords onto four macros:

  | `!!!` keyword | Macro Confluence **stores** | Panel Confluence **displays** |
  |---|---|---|
  | `info`, `note`, `abstract`, `example`, `question`, `quote` | `info` | Info — blue "i" |
  | `success`, `tip`, `hint` | `tip` | Success — green check |
  | `warning`, `attention`, `important` | `note` | Warning — orange "!" |
  | `error`, `danger`, `bug`, `caution`, `failure` | `warning` | Error — red "x" |

  So `!!! tip` and `!!! success` are the same macro, and `!!! note` produces an **Info** panel
  rather than a warning of any kind. **A keyword outside this table is not a surprise panel — it is
  a hard failure**: `DocumentError: unsupported admonition type: <word>`, which aborts the whole
  conversion. Confluence's own **Note** panel is unreachable by any keyword: it needs an
  `ac:adf-extension` tree md2conf does not generate.

  `--use-panel` (below) accepts the same seventeen plus `disclaimer` and `flag`, so those two
  convert only with that flag and fail without it.
- **Every page gets an `info` banner you did not write.** md2conf prepends an `info` macro reading
  "This page has been generated with a tool." above the `<h1>` of every page, by default. It is the
  reason a converted document always emits one more `info` than its Markdown accounts for.
  `--no-generated-by` removes it and `--generated-by MARKDOWN` replaces the wording; both are
  pass-through. Mention it before a first publish — an author who did not expect it reads it as a
  defect.
- **Four flags change what is emitted**, and all are pass-through, so they go after `--`:
  `--use-panel` swaps the four admonition macros for `panel`; `--no-render-latex` emits maths
  macros instead of rasterising formulas to attached images; `--heading-anchors` adds an `anchor`
  to every heading; `--no-generated-by` drops the banner above. Say which one you passed when
  reporting a publish.
- **Anything unmodelled goes through a `csf` fenced block**, which passes Confluence storage format
  through untouched — the route for `pagetree`, `view-file` and third-party app macros. Nothing
  validates it, so a malformed macro fails on the page rather than during conversion.
