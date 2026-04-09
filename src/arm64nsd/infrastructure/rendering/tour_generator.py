"""Generate an interactive feature tour of ARM64 NSD capabilities."""

from __future__ import annotations

from html import escape

from arm64nsd.domain.model import SourceUnit
from arm64nsd.domain.ports import Arm64ControlFlowExtractor
from arm64nsd.infrastructure.rendering.nassi_html_renderer import HtmlNassiDiagramRenderer


# ---------------------------------------------------------------------------
# Tour examples — each exercises a specific control-flow pattern
# ---------------------------------------------------------------------------

TOUR_EXAMPLES: tuple[dict[str, str], ...] = (
    {
        "id": "sequence",
        "title": "Sequence",
        "description": "Linear execution — instructions run one after another with no branching.",
        "source": """\
    .global _sequence
_sequence:
    stp x29, x30, [sp, #-16]!
    mov x0, #10
    add x0, x0, #5
    sub x1, x0, #3
    ldp x29, x30, [sp], #16
    ret
""",
    },
    {
        "id": "if-only",
        "title": "If (Conditional)",
        "description": "One-way branch — the then-block executes only when the condition is true.",
        "source": """\
    .global _abs_value
_abs_value:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    cmp x0, #0
    b.ge .Lpositive
    neg x0, x0
.Lpositive:
    ldp x29, x30, [sp], #16
    ret
""",
    },
    {
        "id": "if-else",
        "title": "If / Else",
        "description": "Two-way branch — one path when the condition is true, another when false.",
        "source": """\
    .global _abs_diff
_abs_diff:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    sub x2, x0, x1
    cmp x2, #0
    b.lt _abs_diff_else
    mov x0, x2
    b _abs_diff_end
_abs_diff_else:
    neg x0, x2
_abs_diff_end:
    ldp x29, x30, [sp], #16
    ret
""",
    },
    {
        "id": "while",
        "title": "While Loop",
        "description": "Pre-condition loop — test first, then execute the body while the condition holds.",
        "source": """\
    .global _sum_to_n
_sum_to_n:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    mov x1, #0
    mov x2, #1
_sum_to_n_loop:
    cmp x2, x0
    b.gt _sum_to_n_done
    add x1, x1, x2
    add x2, x2, #1
    b _sum_to_n_loop
_sum_to_n_done:
    mov x0, x1
    ldp x29, x30, [sp], #16
    ret
""",
    },
    {
        "id": "repeat",
        "title": "Repeat-While Loop",
        "description": "Post-condition loop — execute the body first, then test whether to repeat.",
        "source": """\
    .global _delay_cycles
_delay_cycles:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
_delay_body:
    sub x0, x0, #1
    cmp x0, #0
    b.gt _delay_body
    ldp x29, x30, [sp], #16
    ret
""",
    },
    {
        "id": "switch",
        "title": "Switch / Case",
        "description": "Multi-way dispatch — cascading compare-and-branch selects one of several cases.",
        "source": """\
    .global _classify
_classify:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    cmp x0, #0
    b.eq _classify_zero
    cmp x0, #1
    b.eq _classify_one
    cmp x0, #2
    b.eq _classify_two
    b _classify_default
_classify_zero:
    mov x0, #0
    b _classify_end
_classify_one:
    mov x0, #1
    b _classify_end
_classify_two:
    mov x0, #2
    b _classify_end
_classify_default:
    mvn x0, xzr
_classify_end:
    ldp x29, x30, [sp], #16
    ret
""",
    },
    {
        "id": "nested",
        "title": "Nested: If inside While",
        "description": "An if-block nested within a while-loop — the most common compound pattern.",
        "source": """\
    .global _filter_range
_filter_range:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    mov x4, #0
    mov x5, #0
_filter_range_loop:
    cmp x5, x3
    b.ge _filter_range_done
    ldr x6, [x0, x5, lsl #3]
    cmp x6, x1
    b.lt _filter_range_next
    cmp x6, x2
    b.gt _filter_range_next
    add x4, x4, #1
_filter_range_next:
    add x5, x5, #1
    b _filter_range_loop
_filter_range_done:
    mov x0, x4
    ldp x29, x30, [sp], #16
    ret
""",
    },
)


# ---------------------------------------------------------------------------
# Tour renderer
# ---------------------------------------------------------------------------

class TourGenerator:
    """Generate a self-contained HTML feature tour."""

    def __init__(
        self,
        extractor: Arm64ControlFlowExtractor,
        renderer: HtmlNassiDiagramRenderer,
    ) -> None:
        self._extractor = extractor
        self._renderer = renderer

    def generate(self) -> str:
        sections = "".join(self._render_section(ex) for ex in TOUR_EXAMPLES)
        nav_items = "".join(
            f'<a class="nav-link" href="#{escape(ex["id"])}">'
            f'<span class="nav-num">{i + 1:02d}</span> {escape(ex["title"])}'
            f"</a>"
            for i, ex in enumerate(TOUR_EXAMPLES)
        )
        return _TOUR_HTML.format(nav=nav_items, sections=sections)

    def _render_section(self, example: dict[str, str]) -> str:
        source_unit = SourceUnit(
            identifier=example["id"],
            location=example["id"],
            content=example["source"],
        )
        diagram = self._extractor.extract(source_unit)
        functions_html = "".join(
            self._renderer._render_function(fn) for fn in diagram.functions
        )
        if not functions_html:
            functions_html = '<p class="empty-file">No functions detected.</p>'

        source_escaped = escape(example["source"].strip())
        return (
            f'<section class="tour-section" id="{escape(example["id"])}">'
            f'<div class="section-header">'
            f'<span class="section-num">{TOUR_EXAMPLES.index(example) + 1:02d}</span>'
            f'<h2>{escape(example["title"])}</h2>'
            f'<p>{escape(example["description"])}</p>'
            f"</div>"
            f'<div class="section-columns">'
            f'<div class="column column-source">'
            f'<div class="column-title">ARM64 Source</div>'
            f'<pre class="source-block"><code>{source_escaped}</code></pre>'
            f"</div>"
            f'<div class="column column-diagram">'
            f'<div class="column-title">Nassi-Shneiderman Diagram</div>'
            f'<div class="diagram-body">{functions_html}</div>'
            f"</div>"
            f"</div>"
            f"</section>"
        )


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_TOUR_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ARM64 Nassi-Shneiderman Feature Tour</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg:          #0a0f18;
      --bg-accent:   #10182a;
      --surface:     #111827;
      --surface-2:   #172131;
      --surface-3:   #1c2940;
      --surface-4:   #233452;
      --border:      #2b3b59;
      --border-strong: #3f5378;
      --border-soft: #182338;
      --text:        #cfd8f6;
      --text-bright: #f4f7ff;
      --muted:       #8e9bbb;
      --blue:        #82aaff;
      --blue-dim:    #243b69;
      --green:       #a6da95;
      --green-dim:   #163628;
      --red:         #ff93a9;
      --red-dim:     #371925;
      --orange:      #ffb86b;
      --orange-dim:  #37230f;
      --teal:        #56d4dd;
      --teal-dim:    #11343b;
      --purple:      #c4a7ff;
      --purple-dim:  #2a1d41;
      --amber:       #f1ca7a;
      --amber-dim:   #39290f;
      --loop-fill:   #132033;
      --switch-fill: #102529;
      --yes-fill:    #102217;
      --no-fill:     #251019;
      --action-fill: var(--surface-2);
      --note-fill:   #101720;
      --mono: "JetBrains Mono", "Fira Code", "Cascadia Code", "SF Mono", "Menlo", monospace;
      --ui:   "IBM Plex Sans", -apple-system, "Segoe UI", system-ui, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: var(--ui);
      font-size: 14px;
      color: var(--text);
      background:
        radial-gradient(circle at top, rgba(130, 170, 255, 0.10), transparent 28%),
        linear-gradient(180deg, var(--bg) 0%, #0c121d 100%);
      min-height: 100vh;
      color-scheme: dark;
      -webkit-font-smoothing: antialiased;
    }}

    /* ── Hero ── */
    .hero {{
      text-align: center;
      padding: 56px 24px 36px;
      border-bottom: 1px solid var(--border);
    }}
    .hero-badge {{
      display: inline-block;
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--blue);
      background: rgba(130, 170, 255, 0.14);
      border: 1px solid rgba(130, 170, 255, 0.3);
      border-radius: 999px;
      padding: 4px 12px;
      margin-bottom: 16px;
    }}
    .hero h1 {{
      font-size: 28px;
      font-weight: 700;
      color: var(--text-bright);
      letter-spacing: -0.02em;
      margin-bottom: 10px;
    }}
    .hero p {{
      font-size: 15px;
      color: var(--muted);
      max-width: 640px;
      margin: 0 auto;
      line-height: 1.6;
    }}

    /* ── Nav ── */
    .tour-nav {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(10, 15, 24, 0.92);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 0 24px;
      display: flex;
      gap: 4px;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    .nav-link {{
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 10px 14px;
      color: var(--muted);
      text-decoration: none;
      font-size: 12.5px;
      font-weight: 500;
      white-space: nowrap;
      border-bottom: 2px solid transparent;
      transition: color 0.15s, border-color 0.15s;
    }}
    .nav-link:hover {{
      color: var(--text-bright);
      border-bottom-color: var(--blue);
    }}
    .nav-num {{
      font-family: var(--mono);
      font-size: 10px;
      font-weight: 700;
      color: var(--blue);
      background: var(--blue-dim);
      border-radius: 4px;
      padding: 1px 5px;
    }}

    /* ── Section ── */
    .tour-section {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 48px 24px;
      border-bottom: 1px solid var(--border-soft);
    }}
    .section-header {{
      margin-bottom: 24px;
    }}
    .section-num {{
      display: inline-block;
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 700;
      color: var(--purple);
      background: var(--purple-dim);
      border: 1px solid rgba(196, 167, 255, 0.3);
      border-radius: 6px;
      padding: 2px 8px;
      margin-bottom: 8px;
    }}
    .section-header h2 {{
      font-size: 22px;
      font-weight: 700;
      color: var(--text-bright);
      margin-bottom: 6px;
    }}
    .section-header p {{
      font-size: 14px;
      color: var(--muted);
      line-height: 1.5;
    }}

    /* ── Two-column layout ── */
    .section-columns {{
      display: grid;
      grid-template-columns: minmax(320px, 1fr) minmax(400px, 1.5fr);
      gap: 20px;
      align-items: start;
    }}
    .column-title {{
      font-family: var(--mono);
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--blue);
      margin-bottom: 8px;
    }}
    .column-source {{
      position: sticky;
      top: 56px;
    }}
    .source-block {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      overflow-x: auto;
    }}
    .source-block code {{
      display: block;
      font-family: var(--mono);
      font-size: 12.5px;
      line-height: 1.75;
      color: var(--text-bright);
      white-space: pre;
      tab-size: 4;
    }}

    /* ── Diagram column ── */
    .diagram-body {{
      background:
        linear-gradient(180deg, rgba(255,255,255,0.015), rgba(255,255,255,0)),
        var(--bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      overflow-x: auto;
    }}

    /* ── Footer ── */
    .tour-footer {{
      text-align: center;
      padding: 32px 24px;
      color: var(--muted);
      font-size: 12px;
    }}
    .tour-footer a {{
      color: var(--blue);
      text-decoration: none;
    }}

    /* ── NSD styles (imported from renderer) ── */
    .function-panel {{
      margin-bottom: 16px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: rgba(10, 15, 24, 0.72);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
      overflow: hidden;
    }}
    .function-panel:last-child {{ margin-bottom: 0; }}
    .function-head {{
      padding: 12px 16px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)),
        var(--surface-3);
      border-bottom: 1px solid var(--border-strong);
    }}
    .function-title {{
      font-size: 15px;
      font-weight: 600;
      color: var(--text-bright);
      line-height: 1.3;
    }}
    .function-signature {{
      margin-top: 5px;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.6;
      color: var(--muted);
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .function-body {{
      padding: 12px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0)),
        rgba(7, 11, 18, 0.84);
    }}
    .function-body > .ns-sequence {{
      width: max-content;
      min-width: 100%;
    }}
    .ns-sequence {{
      display: flex;
      flex-direction: column;
      width: max-content;
      min-width: 100%;
    }}
    .ns-sequence > .ns-node + .ns-node,
    .ns-cases > .case + .case,
    .ns-catches > .ns-node + .ns-node {{
      margin-top: -1px;
    }}
    .ns-node {{
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--action-fill);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
    }}
    .ns-header,
    .ns-footer,
    .case-title {{
      padding: 7px 12px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0)),
        var(--blue-dim);
      color: var(--text-bright);
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 500;
      line-height: 1.4;
      border-bottom: 1px solid var(--border-strong);
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .ns-footer {{
      border-top: 1px solid var(--border);
      border-bottom: 0;
    }}
    .ns-label,
    .empty,
    .ns-note {{
      padding: 8px 12px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.015), rgba(255,255,255,0)),
        var(--action-fill);
    }}
    .action-text {{
      display: block;
      font-family: var(--mono);
      font-size: 13px;
      line-height: 1.72;
      color: var(--text-bright);
      letter-spacing: -0.01em;
      font-variant-ligatures: none;
      tab-size: 2;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
    .ns-loop,
    .ns-repeat  {{ background: var(--loop-fill); }}
    .ns-switch  {{ background: var(--switch-fill); }}
    .ns-switch  > .ns-header,
    .case-title              {{ background: var(--teal-dim);   color: var(--teal);   }}
    .ns-node.ns-loop,
    .ns-node.ns-repeat  {{ border-left: 3px solid var(--blue); }}
    .ns-node.ns-switch  {{ border-left: 3px solid var(--teal); }}
    .ns-depth-1 > .ns-node {{ background-color: rgba(255,255,255,0.012); }}
    .ns-depth-2 > .ns-node {{ background-color: rgba(255,255,255,0.020); }}
    .ns-depth-3 > .ns-node {{ background-color: rgba(255,255,255,0.028); }}
    .ns-if-cap {{
      border-bottom: 1px solid var(--border);
      line-height: 0;
    }}
    .ns-if-svg {{
      display: block;
      height: auto;
    }}
    .ns-if-triangle {{
      fill: var(--blue-dim);
      stroke: var(--border);
      stroke-width: 1;
    }}
    .ns-if-diagonal {{
      stroke: var(--border);
      stroke-width: 1;
    }}
    .ns-if-condition-fo {{
      overflow: hidden;
    }}
    .ns-if-condition-text {{
      font-family: var(--mono);
      font-size: 13px;
      font-weight: 500;
      color: var(--text-bright);
      text-align: center;
      word-break: break-word;
      overflow-wrap: anywhere;
      line-height: 1.3;
      padding: 4px 8px;
    }}
    .ns-if-label-yes {{
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      fill: var(--green);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .ns-if-label-no {{
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      fill: var(--red);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .ns-switch-header {{
      padding: 9px 12px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0)),
        var(--teal-dim);
      color: var(--text-bright);
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 500;
      border-bottom: 1px solid var(--border-strong);
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .ns-switch-cases {{
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(140px, max-content);
      background: var(--bg);
      width: max-content;
      min-width: 100%;
    }}
    .ns-switch-case-col {{
      border-right: 1px solid var(--border);
      min-width: 140px;
      display: flex;
      flex-direction: column;
    }}
    .ns-switch-case-col:last-child {{
      border-right: none;
    }}
    .ns-switch-case-value {{
      padding: 9px 12px;
      background: rgba(16, 24, 39, 0.86);
      color: var(--teal);
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 600;
      border-bottom: 1px solid var(--border-strong);
      text-align: center;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .ns-switch-case-body {{
      padding: 0;
      background: var(--bg);
      min-height: 40px;
    }}
    .ns-switch-case-body .ns-sequence {{
      padding: 8px;
    }}
    /* Depth-coded triangles (0-50) */
    .ns-if-depth-0-triangle {{ fill: var(--blue-dim); stroke: var(--blue); }}
    .ns-if-depth-0-diagonal {{ stroke: var(--blue); }}
    .ns-if-depth-1-triangle {{ fill: var(--green-dim); stroke: var(--green); }}
    .ns-if-depth-1-diagonal {{ stroke: var(--green); }}
    .ns-if-depth-2-triangle {{ fill: var(--purple-dim); stroke: var(--purple); }}
    .ns-if-depth-2-diagonal {{ stroke: var(--purple); }}
    .ns-if-depth-3-triangle {{ fill: var(--teal-dim); stroke: var(--teal); }}
    .ns-if-depth-3-diagonal {{ stroke: var(--teal); }}
    .ns-if-depth-4-triangle {{ fill: var(--amber-dim); stroke: var(--amber); }}
    .ns-if-depth-4-diagonal {{ stroke: var(--amber); }}
    .ns-if-depth-5-triangle {{ fill: var(--blue-dim); stroke: var(--blue); }}
    .ns-if-depth-5-diagonal {{ stroke: var(--blue); }}
    .ns-branches {{
      display: grid;
      grid-template-columns: repeat(2, max-content);
      background: var(--surface-2);
      width: max-content;
      min-width: 100%;
    }}
    .ns-branches-single {{ grid-template-columns: max-content; }}
    .ns-branch {{
      border-left: 2px solid var(--border);
      background: var(--surface-2);
    }}
    .ns-branch-yes {{ background: rgba(158, 206, 106, 0.08); }}
    .ns-branch-no  {{ background: rgba(247, 118, 142, 0.08); }}
    .ns-branch-yes > .ns-sequence > .ns-node {{ background: rgba(158, 206, 106, 0.12); }}
    .ns-branch-no  > .ns-sequence > .ns-node {{ background: rgba(247, 118, 142, 0.12); }}
    .ns-branch-yes .ns-label,
    .ns-branch-yes .empty,
    .ns-branch-yes .ns-note {{ background: rgba(158, 206, 106, 0.14); }}
    .ns-branch-no .ns-label,
    .ns-branch-no .empty,
    .ns-branch-no .ns-note {{ background: rgba(247, 118, 142, 0.14); }}
    .ns-branch-yes > .ns-branch-title {{ background: rgba(158, 206, 106, 0.2); color: var(--green); }}
    .ns-branch-no  > .ns-branch-title {{ background: rgba(247, 118, 142, 0.18); color: var(--red); }}
    .ns-branch:first-child {{ border-left: 0; }}
    .ns-branch-title {{
      padding: 7px 12px;
      border-bottom: 1px solid var(--border);
      background: rgba(18, 26, 41, 0.92);
      color: var(--muted);
      font-size: 10.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .ns-cases {{ background: var(--surface-2); }}
    .case {{ border-top: 1px solid var(--border); }}
    .case:first-child {{ border-top: 0; }}
    .ns-catches {{ border-top: 1px solid var(--border); }}
    .empty {{
      color: var(--muted);
      font-style: italic;
      font-size: 12px;
      background: rgba(20, 28, 41, 0.92);
    }}
    .ns-note {{
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
      font-style: italic;
      background: var(--note-fill);
      border-top: 1px solid var(--border);
      padding: 8px 12px;
    }}
    .empty-file {{
      padding: 24px;
      color: var(--muted);
    }}

    @media (max-width: 900px) {{
      .section-columns {{
        grid-template-columns: 1fr;
      }}
      .column-source {{
        position: static;
      }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="hero-badge">arm64-v8a-nsd</div>
    <h1>ARM64 Nassi-Shneiderman Feature Tour</h1>
    <p>Interactive showcase of every control-flow pattern recognised by the ARM64 NSD diagram generator — from simple sequences to nested loops.</p>
  </header>
  <nav class="tour-nav">
    {nav}
  </nav>
  <main>
    {sections}
  </main>
  <footer class="tour-footer">
    Generated by <a href="https://github.com">arm64nsd</a> &mdash; ARM64 v8-A Nassi-Shneiderman Diagram Generator
  </footer>
</body>
</html>
"""
