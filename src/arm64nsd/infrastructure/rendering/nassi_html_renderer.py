"""Render structured control flow as Nassi-Shneiderman HTML."""

from __future__ import annotations

from html import escape
from math import ceil
import re

from arm64nsd.domain.control_flow import (
    ActionFlowStep,
    BreakStep,
    CallFlowStep,
    ContinueStep,
    ControlFlowDiagram,
    ControlFlowStep,
    EpilogueStep,
    IfFlowStep,
    IndirectBranchStep,
    InlineIfStep,
    InfiniteLoopStep,
    PrologueStep,
    RepeatWhileFlowStep,
    ReturnStep,
    SwitchCaseFlow,
    SwitchFlowStep,
    SystemCallStep,
    TailCallStep,
    WhileFlowStep,
)
from arm64nsd.domain.ports import NassiDiagramRenderer


class HtmlNassiDiagramRenderer(NassiDiagramRenderer):
    # Register patterns for syntax highlighting
    _REG_PATTERNS = {
        # Argument/return registers (x0-x7, w0-w7, v0-v7, d0-d7, s0-s7)
        "arg": re.compile(r"\b([xwvds][0-7])(?!\d)"),
        # Callee-saved registers (x19-x28, w19-w28)
        "callee": re.compile(r"\b([xw][12][0-9]|[xw]2[0-8])(?!\d)"),
        # Special registers (sp, fp, lr, x29, x30, xzr, wzr)
        "special": re.compile(
            r"\b(sp|wsp|fp|xfp|lr|xlr|zr|xzr|wzr|x29|w29|x30|w30)\b", re.IGNORECASE
        ),
        # FP/SIMD registers (v8-v31, d8-d31, s8-s31, q0-q31, h0-h31, b0-b31)
        "fp": re.compile(r"\b([vdsqhb][89]|[1-3][0-9]|[vdsqhb][12][0-9]|[vdsqhb]3[01])(?!\d)"),
        # Temporaries (x8-x18, w8-w18) - will be default color
    }

    def _escape_instruction(self, text: str) -> str:
        """Escape HTML but preserve readable character constants.

        Keeps 'z', 'A', etc. readable instead of &#x27;z&#x27;.
        """
        if not text:
            return text

        # Escape HTML normally
        result = escape(text)

        # Restore readable single quotes in character constants
        # &#x27; is the HTML entity for single quote
        result = result.replace("&#x27;", "'")
        # Also handle the numeric variant &#39;
        result = result.replace("&#39;", "'")

        return result

    def _highlight_registers(self, text: str) -> str:
        """Wrap register names in spans for syntax highlighting."""
        if not text:
            return text

        # Order matters: match more specific patterns first
        replacements = [
            (self._REG_PATTERNS["special"], "reg-special"),
            (self._REG_PATTERNS["callee"], "reg-callee"),
            (self._REG_PATTERNS["arg"], "reg-arg"),
            (self._REG_PATTERNS["fp"], "reg-fp"),
        ]

        result = text
        for pattern, css_class in replacements:

            def replacer(m):
                return f'<span class="{css_class}">{m.group(0)}</span>'

            result = pattern.sub(replacer, result)

        return result

    def _depth_badge(self, i: int) -> str:
        if i == 0:
            return ""
        if i <= 20:
            return f" {chr(0x2460 + i - 1)}"
        if i <= 35:
            return f" {chr(0x3251 + i - 21)}"
        return f" {chr(0x32B1 + i - 36)}"

    def _depth_css(self) -> str:
        colors = ["blue", "green", "purple", "teal", "amber"]
        rules = []
        for i in range(51):
            c = colors[i % 5]
            rules.append(
                f"      .ns-if-depth-{i}-triangle {{ fill: var(--{c}-dim); stroke: var(--{c}); }}"
            )
            rules.append(f"      .ns-if-depth-{i}-diagonal {{ stroke: var(--{c}); }}")
        return "\n".join(rules)

    def render(self, diagram: ControlFlowDiagram) -> str:
        sections = "".join(self._render_function(function) for function in diagram.functions)
        if not sections:
            sections = '<section class="function-panel"><p class="empty-file">No functions found.</p></section>'

        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Nassi-Shneiderman Control Flow</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <!-- Highlight.js for syntax highlighting -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/asm.min.js"></script>
    <script>
      document.addEventListener('DOMContentLoaded', function() {{
        document.querySelectorAll('pre.hljs').forEach(function(block) {{
          hljs.highlightElement(block);
        }});
      }});
    </script>
    <style>
      :root {{
        /* Palette — editor-first dark */
        --bg:          #0a0f18;
        --bg-accent:   #10182a;
        --surface:     #111827;
        --surface-2:   #172131;
        --surface-3:   #1c2940;
        --surface-4:   #233452;
        --border:      #2b3b59;
        --border-strong: #3f5378;
        --border-soft: #182338;
        --text:        #e6edf3;
        --text-bright: #ffffff;
--muted: #94a3b8;
        --shadow:      0 24px 72px rgba(3, 8, 18, 0.56);

        /* Accent colours */
--blue: #60a5fa;
--blue-dim: #1e4a8a;
--green: #65f0b1;
--green-dim: #116650;
--red: #f472b6;
--red-dim: #912d6c;
--orange: #fb923c;
--orange-dim: #92400e;
--teal: #2dd4bf;
--teal-dim: #0f766e;
--purple: #c084fc;
--purple-dim: #6e1a9d;
--amber: #fbbf24;
--amber-dim: #a16207;

/* Block fills */
         --loop-fill:   #1a2337;
         --switch-fill: #182a33;
         --yes-fill:    #1b2a21;
         --no-fill:     #2a1925;
         --action-fill: var(--surface-2);
         --note-fill:   #15202b;

        /* Code font */
        --mono: "JetBrains Mono", "Fira Code", "Cascadia Code", "SF Mono", "Menlo", monospace;
        --ui: "Inter", -apple-system, "Segoe UI", system-ui, sans-serif;
      }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        font-family: var(--ui);
        font-size: 14px;
        color: var(--text);
background:
           radial-gradient(circle at top right, rgba(96, 165, 250, 0.08), transparent 40%),
           radial-gradient(circle at bottom left, rgba(244, 117, 182, 0.08), transparent 40%),
           linear-gradient(180deg, var(--bg) 0%, #0b1219 100%);
        padding: 24px;
        min-height: 100vh;
        overflow-x: auto;
        color-scheme: dark;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
      }}
      /* ── Viewer shell ── */
      .viewer {{
        width: max-content;
        min-width: min(1200px, calc(100vw - 48px));
        margin: 0 auto;
        border: 1px solid var(--border-strong);
        border-radius: 14px;
        background:
          linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)),
          var(--surface);
        box-shadow: var(--shadow);
        overflow: hidden;
      }}
.titlebar {{
         padding: 10px 16px;
         background: linear-gradient(135deg, var(--blue-dim) 0%, var(--purple-dim) 100%);
         border-bottom: 1px solid var(--border-strong);
         display: flex;
         align-items: center;
         gap: 10px;
         border-top-left-radius: 10px;
         border-top-right-radius: 10px;
         box-shadow: 0 4px 12px rgba(0,0,0,0.1);
         transition: all 0.3s ease;
       }}
      .titlebar-icon {{
        width: 14px; height: 14px;
        border-radius: 50%;
        background: var(--blue-dim);
        border: 1px solid var(--blue);
        flex-shrink: 0;
      }}
      .titlebar-text {{
        font-size: 13.5px;
        font-weight: 600;
        color: var(--text-bright);
        letter-spacing: 0.01em;
      }}
      .toolbar {{
        padding: 9px 16px;
        border-bottom: 1px solid var(--border-soft);
        background:
          linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0)),
          var(--surface);
        display: flex;
        flex-wrap: wrap;
        gap: 8px 14px;
        align-items: baseline;
      }}
      .toolbar-label {{
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--blue);
        background: rgba(130, 170, 255, 0.14);
        border: 1px solid rgba(130, 170, 255, 0.3);
        border-radius: 999px;
        padding: 3px 8px;
        white-space: nowrap;
      }}
      .toolbar-path {{
        font-family: var(--mono);
        font-size: 12px;
        color: var(--muted);
        overflow-wrap: anywhere;
      }}
      /* ── Viewer body ── */
      .viewer-body {{
        padding: 16px;
        background:
          linear-gradient(180deg, rgba(255,255,255,0.015), rgba(255,255,255,0) 180px),
          var(--bg);
      }}
      /* ── Function panel ── */
.function-panel {{
         margin-bottom: 16px;
         border: 1px solid var(--border);
         border-radius: 10px;
         background: rgba(15, 23, 42, 0.9);
         box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255,255,255,0.02);
         overflow: hidden;
         transition: transform 0.3s ease, box-shadow 0.3s ease;
       }}
       .function-panel:hover {{
         transform: translateY(-2px);
         box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.02);
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
      /* ── Node sequence ── */
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
         transition: all 0.2s ease;
       }}
      /* ── Block headers/footers ── */
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
      /* ── Action label ── */
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
      /* ── Register syntax highlighting ── */
      .reg-arg {{
        color: #7dd3fc;
        font-weight: 500;
      }}
      .reg-callee {{
        color: var(--green);
        font-weight: 500;
      }}
      .reg-special {{
        color: var(--orange);
        font-weight: 600;
      }}
      .reg-fp {{
        color: var(--purple);
        font-weight: 500;
      }}
      /* ── Block type colours ── */
      .ns-loop,
      .ns-repeat  {{ background: var(--loop-fill); }}
      .ns-switch  {{ background: var(--switch-fill); }}

      .ns-switch  > .ns-header,
      .case-title              {{ background: var(--teal-dim);   color: var(--teal);   }}

      /* Left accent stripes */
      .ns-node.ns-loop,
      .ns-node.ns-repeat  {{ border-left: 3px solid var(--blue); }}
      .ns-node.ns-switch  {{ border-left: 3px solid var(--teal); }}
      .ns-node.ns-call    {{ border-left: 3px solid var(--orange); background: var(--orange-dim); }}
      .ns-node.ns-tailcall {{ border-left: 3px solid var(--amber); background: var(--amber-dim); }}
      .ns-tailcall .call-text {{ color: var(--amber); }}
      .ns-node.ns-return  {{ border-left: 3px solid var(--muted); background: rgba(20, 28, 41, 0.92); }}
      .ns-node.ns-infinite {{ border-left: 3px solid var(--red); background: var(--red-dim); }}
      .ns-node.ns-break,
      .ns-node.ns-continue {{ border-left: 3px solid var(--amber); background: var(--amber-dim); }}
      .ns-node.ns-inline-if {{ border-left: 3px solid var(--purple); background: var(--purple-dim); }}
      .ns-node.ns-indirect {{ border-left: 3px solid var(--teal); background: var(--teal-dim); }}
      .ns-node.ns-prologue {{ border-left: 3px solid var(--green); background: var(--green-dim); }}
      .ns-node.ns-epilogue {{ border-left: 3px solid var(--red); background: var(--red-dim); }}
      .ns-node.ns-syscall {{ border-left: 3px solid #f7768e; background: rgba(247, 118, 142, 0.12); }}
      .stack-text {{
        display: block;
        font-family: var(--mono);
        font-size: 12px;
        line-height: 1.65;
        color: var(--text);
        white-space: pre-wrap;
        overflow-wrap: anywhere;
      }}
      .ns-prologue .stack-text {{ color: var(--green); }}
      .ns-epilogue .stack-text {{ color: var(--red); }}
      .stack-arrow {{
        display: inline-block;
        font-size: 14px;
        margin-right: 6px;
        vertical-align: middle;
        line-height: 1;
      }}
      .ns-prologue .stack-arrow {{ color: var(--green); }}
      .ns-epilogue .stack-arrow {{ color: var(--red); }}
      .stack-badge {{
        display: inline-block;
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 2px 7px;
        border-radius: 3px;
        margin-bottom: 4px;
      }}
      .stack-badge-prologue {{ background: rgba(166, 218, 149, 0.15); color: var(--green); border: 1px solid rgba(166, 218, 149, 0.3); }}
      .stack-badge-epilogue {{ background: rgba(255, 147, 169, 0.12); color: var(--red); border: 1px solid rgba(255, 147, 169, 0.3); }}
      .ns-indirect .call-text {{ color: var(--teal); }}
      .ns-infinite > .ns-header {{ background: var(--red-dim); color: var(--red); }}
      .call-text {{
        display: block;
        font-family: var(--mono);
        font-size: 13px;
        line-height: 1.72;
        color: var(--orange);
        letter-spacing: -0.01em;
        font-variant-ligatures: none;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
      }}
      .return-text {{
        display: block;
        font-family: var(--mono);
        font-size: 13px;
        line-height: 1.72;
        color: var(--muted);
        font-style: italic;
        letter-spacing: -0.01em;
      }}
      .syscall-text {{
        display: block;
        font-family: var(--mono);
        font-size: 13px;
        line-height: 1.72;
        color: #f7768e;
        font-weight: 500;
        letter-spacing: -0.01em;
      }}
      .syscall-badge {{
        display: inline-block;
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 2px 7px;
        border-radius: 3px;
        margin-bottom: 4px;
        background: rgba(247, 118, 142, 0.15);
        color: #f7768e;
        border: 1px solid rgba(247, 118, 142, 0.3);
      }}
      .inline-if-text {{
        display: block;
        font-family: var(--mono);
        font-size: 13px;
        line-height: 1.72;
        color: var(--text);
      }}
      .inline-if-badge {{
        display: inline-block;
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 2px 7px;
        border-radius: 3px;
        margin-bottom: 4px;
        background: rgba(196, 167, 255, 0.15);
        color: var(--purple);
        border: 1px solid rgba(196, 167, 255, 0.3);
      }}
      .inline-if-cond {{
        color: var(--purple);
        font-weight: 500;
      }}

      /* Depth tinting */
      .ns-depth-1 > .ns-node {{ background-color: rgba(255,255,255,0.012); }}
      .ns-depth-2 > .ns-node {{ background-color: rgba(255,255,255,0.020); }}
      .ns-depth-3 > .ns-node {{ background-color: rgba(255,255,255,0.028); }}

      /* ── If/else branches (classic NS diagram with SVG) ── */
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

      /* ── Switch/case (classic NS diagram) ── */
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

      /* Depth-coded if-cap triangles and diagonals (0-50, cycling blue→green→purple→teal→amber) */
{self._depth_css()}

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
         transition: all 0.2s ease;
       }}
      .ns-branch-yes {{
        background: rgba(158, 206, 106, 0.08);
      }}
      .ns-branch-no {{
        background: rgba(247, 118, 142, 0.08);
      }}
      .ns-branch-yes > .ns-sequence > .ns-node {{
        background: rgba(158, 206, 106, 0.12);
      }}
      .ns-branch-no > .ns-sequence > .ns-node {{
        background: rgba(247, 118, 142, 0.12);
      }}
      .ns-branch-yes .ns-label,
      .ns-branch-yes .empty,
      .ns-branch-yes .ns-note {{
        background: rgba(158, 206, 106, 0.14);
      }}
      .ns-branch-no .ns-label,
      .ns-branch-no .empty,
      .ns-branch-no .ns-note {{
        background: rgba(247, 118, 142, 0.14);
      }}
      .ns-branch-yes > .ns-branch-title {{
        background: rgba(158, 206, 106, 0.2);
        color: var(--green);
      }}
      .ns-branch-no > .ns-branch-title {{
        background: rgba(247, 118, 142, 0.18);
        color: var(--red);
      }}
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
         transition: all 0.2s ease;
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
.modal {{
         display: none;
         position: fixed;
         z-index: 1000;
         left: 0;
         top: 0;
         width: 100%;
         height: 100%;
         overflow: auto;
         background-color: rgba(0,0,0,0.7);
         animation: fadeIn 0.3s ease;
       }}
       @keyframes fadeIn {{
         from {{ opacity: 0; }}
         to {{ opacity: 1; }}
       }}
       .modal-content {{
         background-color: var(--surface);
         margin: 5% auto;
         padding: 20px;
         border-radius: 12px;
         border: 1px solid var(--border);
         width: 80%;
         max-width: 1000px;
         box-shadow: 0 20px 60px rgba(0,0,0,0.5);
         animation: slideDown 0.3s ease;
       }}
       @keyframes slideDown {{
         from {{ transform: translateY(-50px); opacity: 0; }}
         to {{ transform: translateY(0); opacity: 1; }}
       }}
       .close-btn {{
         color: var(--muted);
         float: right;
         font-size: 28px;
         font-weight: bold;
         cursor: pointer;
         transition: color 0.2s ease;
       }}
       .close-btn:hover {{
         color: var(--red);
       }}
       .modal-title {{
         font-size: 20px;
         font-weight: 600;
         color: var(--text-bright);
         margin-bottom: 16px;
         border-bottom: 1px solid var(--border);
         padding-bottom: 8px;
       }}
       .code-block {{
         background-color: var(--bg-accent);
         color: var(--text);
         padding: 16px;
         border-radius: 8px;
         overflow-x: auto;
         font-family: var(--mono);
         font-size: 14px;
         line-height: 1.5;
         white-space: pre;
         max-height: 500px;
         overflow-y: auto;
       }}
       .modal-footer {{
         margin-top: 20px;
         text-align: right;
       }}
       .close-modal-btn {{
         background-color: var(--blue);
         color: white;
         border: none;
         padding: 8px 16px;
         border-radius: 6px;
         cursor: pointer;
         font-size: 14px;
         transition: background-color 0.2s ease;
       }}
       .close-modal-btn:hover {{
         background-color: var(--blue-dim);
       }}
       .toolbar-btn {{
         background-color: var(--blue);
         color: white;
         border: none;
         padding: 6px 12px;
         border-radius: 6px;
         cursor: pointer;
         font-size: 13px;
         margin-left: 8px;
         transition: all 0.2s ease;
       }}
       .toolbar-btn:hover {{
         background-color: var(--blue-dim);
         transform: translateY(-1px);
       }}
       .view-code-btn {{
         background-color: var(--green-dim);
       }}
       .view-code-btn:hover {{
         background-color: var(--green);
       }}

      @media (max-width: 800px) {{
        body {{ padding: 12px; }}
        .viewer {{
          width: auto;
          min-width: 0;
        }}
        .viewer-body {{ padding: 8px; }}
        .function-body {{
          padding: 6px;
          overflow-x: auto;
        }}
        .function-body > .ns-sequence,
        .ns-sequence {{
          width: 100%;
          min-width: 0;
        }}
        .ns-branches {{
          width: 100%;
          min-width: 0;
          grid-template-columns: 1fr;
        }}
        .ns-branches-single {{ grid-template-columns: 1fr; }}
        .ns-branch {{
          border-left: 0;
          border-top: 1px solid var(--border);
        }}
        .ns-branch:first-child {{ border-top: 0; }}
      }}
    </style>
  </head>
  <body>
    <div class="viewer">
      <div class="titlebar">
        <div class="titlebar-icon"></div>
        <span class="titlebar-text">ARM64 · NSD Viewer</span>
      </div>
      <div class="toolbar">
        <span class="toolbar-label">Nassi-Shneiderman</span>
        <code class="toolbar-path">{escape(diagram.source_location)}</code>
        <a href="{escape(diagram.source_location)}" target="_blank" class="toolbar-btn view-code-btn">View Code</a>
      </div>
      <!-- Hidden modal for code viewing -->
      <div id="codeModal" class="modal">
        <div class="modal-content">
          <span class="close-btn" onclick="closeCodeModal()">&times;</span>
          <h3 class="modal-title">Source Code</h3>
          <pre class="code-block hljs language-asm"><code id="modalCode"></code></pre>
          <div class="modal-footer">
            <button class="close-modal-btn" onclick="closeCodeModal()">Close</button>
          </div>
        </div>
      </div>
      <script>
        // Get the modal
        var modal = document.getElementById('codeModal');
        
        // Get the button that opens the modal
        var btn = document.querySelector('.view-code-btn');
        
        // Get the <span> element that closes the modal
        var span = document.getElementsByClassName('close-btn')[0];
        var closeBtn = document.querySelector('.close-modal-btn');
        
        // When the user clicks the button, open the modal AND load code
        btn.onclick = function() {{
          modal.style.display = 'block';
          var codePath = btn.getAttribute('data-code-path');
          if (!codePath) {{
            // Fallback to current source location
            codePath = '{escape(diagram.source_location)}';
          }}
          fetchCode(codePath);
        }}
        
        // When the user clicks on <span> (x), close the modal
        span.onclick = function() {{
          modal.style.display = 'none';
        }}
        
        // When the user clicks on close button, close the modal
        closeBtn.onclick = function() {{
          modal.style.display = 'none';
        }}
        
        // When the user clicks anywhere outside of the modal, close it
        window.onclick = function(event) {{
          if (event.target == modal) {{
            modal.style.display = 'none';
          }}
        }}
        
        function fetchCode(path) {{
          // Store the path for later use
          btn.setAttribute('data-code-path', path);
          
          // Fetch the file content
          fetch(path)
            .then(response => response.text())
            .then(text => {{
              // Escape HTML and set code
              var codeEl = document.getElementById('modalCode');
              codeEl.textContent = text;
              // Re-highlight with Highlight.js
              hljs.highlightElement(codeEl.parentElement);
            }})
            .catch(error => {{
              console.error('Error fetching file:', error);
              document.getElementById('modalCode').textContent = 'Error loading file.';
            }});
        }}
        
        function showCodeModal(path) {{
          var modal = document.getElementById('codeModal');
          modal.style.display = 'block';
          fetchCode(path);
        }}
        
        function closeCodeModal() {{
          var modal = document.getElementById('codeModal');
          modal.style.display = 'none';
        }}
      </script>
      <main class="viewer-body">{sections}</main>
    </div>
  </body>
</html>
"""

    def _render_function(self, function) -> str:
        return (
            '<section class="function-panel">'
            '<div class="function-head">'
            f'<h2 class="function-title">{escape(function.qualified_name)}</h2>'
            f'<div class="function-signature">{escape(function.signature)}</div>'
            "</div>"
            '<div class="function-body">'
            f"{self._render_sequence(function.steps, depth=0)}"
            "</div>"
            "</section>"
        )

    def _render_sequence(self, steps: tuple[ControlFlowStep, ...], *, depth: int) -> str:
        if not steps:
            return '<div class="empty">No structured steps.</div>'
        rendered = "".join(self._render_step(step, depth=depth) for step in steps)
        return f'<div class="ns-sequence ns-depth-{depth}">{rendered}</div>'

    def _render_step(self, step: ControlFlowStep, *, depth: int) -> str:
        if isinstance(step, ActionFlowStep):
            label_html = self._highlight_registers(self._escape_instruction(step.label))
            return (
                '<div class="ns-node ns-action">'
                f'<div class="ns-label" aria-label="Action {self._escape_instruction(step.label)}">'
                f'<code class="action-text">{label_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, CallFlowStep):
            target_html = self._highlight_registers(self._escape_instruction(step.target))
            return (
                '<div class="ns-node ns-call">'
                f'<div class="ns-label" aria-label="Call {self._escape_instruction(step.target)}">'
                f'<code class="call-text">call {target_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, TailCallStep):
            target_html = self._highlight_registers(self._escape_instruction(step.target))
            return (
                '<div class="ns-node ns-call ns-tailcall">'
                f'<div class="ns-label" aria-label="Tail call {self._escape_instruction(step.target)}">'
                f'<code class="call-text">tail call {target_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, InlineIfStep):
            # Parse instruction like "csel x0, x1, x2, le" into mnemonic + condition
            parts = step.expression.split(maxsplit=1)
            mnemonic = parts[0] if parts else step.expression
            cond = parts[1] if len(parts) > 1 else ""
            mnemonic_html = self._highlight_registers(self._escape_instruction(mnemonic))
            cond_html = (
                f' <span class="inline-if-cond">{self._highlight_registers(self._escape_instruction(cond))}</span>'
                if cond
                else ""
            )
            return (
                '<div class="ns-node ns-inline-if">'
                '<div class="ns-label">'
                '<span class="inline-if-badge">inline if</span>'
                f'<code class="inline-if-text"><br/>{mnemonic_html}{cond_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, IndirectBranchStep):
            reg_html = self._highlight_registers(self._escape_instruction(step.register))
            return (
                '<div class="ns-node ns-indirect">'
                f'<div class="ns-label" aria-label="Indirect branch">'
                f'<code class="call-text">jump {reg_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, ReturnStep):
            return (
                '<div class="ns-node ns-return">'
                '<div class="ns-label" aria-label="Return">'
                '<code class="return-text">ret</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, SystemCallStep):
            number_html = self._highlight_registers(self._escape_instruction(step.number))
            return (
                '<div class="ns-node ns-syscall">'
                '<div class="ns-label">'
                '<span class="syscall-badge">syscall</span>'
                f'<code class="syscall-text"><br/>svc {number_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, InfiniteLoopStep):
            return (
                '<div class="ns-node ns-infinite"><div class="ns-header">Infinite Loop</div></div>'
            )
        if isinstance(step, BreakStep):
            return (
                '<div class="ns-node ns-break">'
                f'<div class="ns-label"><code class="break-text">break {self._escape_instruction(step.label)}</code></div>'
                "</div>"
            )
        if isinstance(step, ContinueStep):
            return (
                '<div class="ns-node ns-continue">'
                f'<div class="ns-label"><code class="break-text">continue {self._escape_instruction(step.label)}</code></div>'
                "</div>"
            )
        if isinstance(step, PrologueStep):
            body = "\n".join(step.instructions)
            body_html = self._highlight_registers(self._escape_instruction(body))
            return (
                '<div class="ns-node ns-prologue">'
                '<div class="ns-label">'
                '<span class="stack-badge stack-badge-prologue"><span class="stack-arrow">\u2193</span>prologue</span>'
                f'<code class="stack-text"><br/>{body_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, EpilogueStep):
            body = "\n".join(step.instructions)
            body_html = self._highlight_registers(self._escape_instruction(body))
            return (
                '<div class="ns-node ns-epilogue">'
                '<div class="ns-label">'
                '<span class="stack-badge stack-badge-epilogue"><span class="stack-arrow">\u2191</span>epilogue</span>'
                f'<code class="stack-text"><br/>{body_html}</code>'
                "</div>"
                "</div>"
            )
        if isinstance(step, IfFlowStep):
            if step.else_steps:
                else_markup = (
                    '<div class="ns-branch ns-branch-no" aria-label="Else branch">'
                    f"{self._render_sequence(step.else_steps, depth=depth + 1)}"
                    "</div>"
                )
                branches_class = "ns-branches"
                trailing_note = ""
            else:
                else_markup = ""
                branches_class = "ns-branches ns-branches-single"
                trailing_note = '<div class="ns-note">No branch continues after the decision.</div>'

            return (
                '<div class="ns-node ns-if">'
                f"{self._render_if_cap(step.condition, depth=depth)}"
                f'<div class="{branches_class}">'
                '<div class="ns-branch ns-branch-yes" aria-label="Then branch">'
                f"{self._render_sequence(step.then_steps, depth=depth + 1)}"
                "</div>"
                f"{else_markup}"
                "</div>"
                f"{trailing_note}"
                "</div>"
            )
        if isinstance(step, WhileFlowStep):
            return self._render_single_body(f"While {step.condition}", step.body_steps, depth=depth)
        if isinstance(step, RepeatWhileFlowStep):
            return (
                '<div class="ns-node ns-repeat">'
                f"{self._render_header('Repeat')}"
                f"{self._render_sequence(step.body_steps, depth=depth + 1)}"
                f"{self._render_footer(f'While {step.condition}')}"
                "</div>"
            )
        if isinstance(step, SwitchFlowStep):
            return self._render_switch(step, depth=depth)
        raise TypeError(f"unsupported step type: {type(step)!r}")

    def _render_single_body(
        self,
        title: str,
        steps: tuple[ControlFlowStep, ...],
        *,
        depth: int,
        css_class: str = "ns-loop",
    ) -> str:
        return (
            f'<div class="ns-node {css_class}">'
            f"{self._render_header(title)}"
            f"{self._render_sequence(steps, depth=depth + 1)}"
            "</div>"
        )

    def _render_header(self, title: str) -> str:
        escaped = escape(title)
        return f'<div class="ns-header" aria-label="{escaped}">{escaped}</div>'

    def _if_cap_geometry(self, condition: str, badge: str) -> tuple[int, int, int, int, int]:
        text = f"{badge} {condition}".strip()
        char_count = max(len(text), 12)
        tokens = [token for token in re.split(r"\s+", text) if token]
        longest_token = max((len(token) for token in tokens), default=char_count)

        content_width = max(
            360,
            min(
                1600,
                max(longest_token * 8 + 48, ceil(char_count / 2) * 7 + 64),
            ),
        )
        svg_width = content_width + 40
        chars_per_line = max(18, int(content_width / 7.4))
        line_count = max(
            1,
            ceil(char_count / chars_per_line),
            ceil(longest_token / chars_per_line),
        )
        text_height = 24 + (line_count - 1) * 17
        split_y = 18 + text_height
        svg_height = split_y + 30
        return svg_width, svg_height, content_width, text_height, split_y

    def _render_if_cap(self, condition: str, *, depth: int = 0) -> str:
        escaped = self._escape_instruction(condition)
        d = min(depth, 50)
        badge = self._depth_badge(d)
        svg_width, svg_height, content_width, text_height, split_y = self._if_cap_geometry(
            condition,
            badge,
        )
        half_width = svg_width / 2
        yes_x = svg_width / 4
        no_x = svg_width * 0.75
        label_y = svg_height - 8

        return (
            f'<div class="ns-if-cap ns-if-depth-{d}" aria-label="If {escaped}">'
            f'<svg class="ns-if-svg" viewBox="0 0 {svg_width} {svg_height}" '
            f'width="{svg_width}" height="{svg_height}" preserveAspectRatio="xMidYMid meet">'
            f'<polygon points="0,0 {svg_width},0 {half_width},{split_y}" '
            f'class="ns-if-triangle ns-if-depth-{d}-triangle"/>'
            f'<foreignObject x="20" y="6" width="{content_width}" height="{text_height}" '
            'class="ns-if-condition-fo">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" class="ns-if-condition-text">{badge} {escaped}</div>'
            "</foreignObject>"
            f'<line x1="0" y1="{split_y}" x2="{half_width}" y2="{svg_height}" '
            f'class="ns-if-diagonal ns-if-depth-{d}-diagonal"/>'
            f'<line x1="{svg_width}" y1="{split_y}" x2="{half_width}" y2="{svg_height}" '
            f'class="ns-if-diagonal ns-if-depth-{d}-diagonal"/>'
            f'<text x="{yes_x}" y="{label_y}" text-anchor="middle" class="ns-if-label-yes">Yes</text>'
            f'<text x="{no_x}" y="{label_y}" text-anchor="middle" class="ns-if-label-no">No</text>'
            "</svg>"
            "</div>"
        )

    def _render_switch(self, step: SwitchFlowStep, *, depth: int) -> str:
        case_count = len(step.cases)
        if case_count == 0:
            return (
                '<div class="ns-node ns-switch">'
                f"{self._render_header(f'Switch {step.expression}')}"
                '<div class="empty">No cases.</div>'
                "</div>"
            )

        # Build case columns with values on top, bodies below
        cases_html = []
        for case in step.cases:
            label = self._normalize_case_label(case.label.strip())
            cases_html.append(
                f'<div class="ns-switch-case-col" aria-label="{escape(label)}">'
                f'<div class="ns-switch-case-value">{escape(label)}</div>'
                f'<div class="ns-switch-case-body">{self._render_sequence(case.steps, depth=depth + 1)}</div>'
                "</div>"
            )

        d = min(depth, 50)
        badge = self._depth_badge(d)

        return (
            f'<div class="ns-node ns-switch ns-if-depth-{d}">'
            f'<div class="ns-switch-header">{badge} switch {self._escape_instruction(step.expression)}</div>'
            f'<div class="ns-switch-cases">{"".join(cases_html)}</div>'
            "</div>"
        )

    def _render_footer(self, title: str) -> str:
        escaped = self._escape_instruction(title)
        return f'<div class="ns-footer" aria-label="{escaped}">{escaped}</div>'

    def _render_case_title(self, label: str) -> str:
        text = self._normalize_case_label(label.strip())
        escaped = escape(text)
        return f'<div class="case-title" aria-label="{escaped}">{escaped}</div>'

    def _normalize_case_label(self, label: str) -> str:
        compact = label.removesuffix(":").strip()
        if compact.startswith("default"):
            return "default"
        if compact.startswith("case "):
            return compact
        return compact
