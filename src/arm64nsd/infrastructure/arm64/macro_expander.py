"""ARM64 assembly macro expansion.

Handles:
- .macro name param1, param2, ... / .endm definitions
- .include "filename" directives
- Macro invocation with parameter substitution
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MacroDefinition:
    """A macro definition with name, parameters, and body lines."""
    name: str
    parameters: tuple[str, ...]
    body: tuple[str, ...]


class MacroExpander:
    """Expands ARM64 macros in assembly source code."""

    def __init__(self, source_resolver: callable[[str], str | None] = None) -> None:
        """Initialize macro expander.

        Args:
            source_resolver: Function that takes a filename and returns source content,
                           or None if file not found. If None, .include is ignored.
        """
        self._macros: dict[str, MacroDefinition] = {}
        self._source_resolver = source_resolver

    def expand(self, source: str, current_file: str = "") -> str:
        """Expand all macros in the source code.

        Args:
            source: Raw assembly source code
            current_file: Path of current file (for resolving .include paths)

        Returns:
            Source code with macros expanded and .include directives processed
        """
        lines = source.split("\n")
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Handle .include directive
            if stripped.lower().startswith(".include"):
                if self._source_resolver:
                    included = self._process_include(stripped, current_file)
                    if included:
                        result.append(included)
                i += 1
                continue

            # Handle .macro definition
            if stripped.lower().startswith(".macro"):
                macro, skip_to = self._parse_macro_definition(lines, i)
                if macro:
                    self._macros[macro.name] = macro
                i = skip_to
                continue

            # Handle macro invocation
            if self._is_macro_invocation(stripped):
                expanded = self._expand_macro_invocation(stripped)
                if expanded:
                    result.append(expanded)
                i += 1
                continue

            # Regular line
            result.append(line)
            i += 1

        return "\n".join(result)

    def _parse_macro_definition(self, lines: list[str], start: int) -> tuple[MacroDefinition | None, int]:
        """Parse a macro definition from .macro to .endm.

        Returns:
            (MacroDefinition or None, index after .endm)
        """
        line = lines[start].strip()
        # .macro name param1, param2, ...
        match = re.match(r'\.macro\s+(\w+)\s*(.*)', line, re.IGNORECASE)
        if not match:
            return None, start + 1

        name = match.group(1)
        params_str = match.group(2).strip()
        parameters = tuple(p.strip() for p in params_str.split(",") if p.strip()) if params_str else ()

        body_lines = []
        i = start + 1
        while i < len(lines):
            if lines[i].strip().lower() == ".endm":
                return MacroDefinition(name=name, parameters=parameters, body=tuple(body_lines)), i + 1
            body_lines.append(lines[i])
            i += 1

        # No .endm found - treat rest of file as macro body
        return MacroDefinition(name=name, parameters=parameters, body=tuple(body_lines)), i

    def _is_macro_invocation(self, line: str) -> bool:
        """Check if line is a macro invocation (not a directive or instruction)."""
        stripped = line.strip()
        if not stripped or stripped.startswith(".") or stripped.startswith("//"):
            return False

        # Check if first word matches a known macro name
        first_word = stripped.split()[0].rstrip(":")
        return first_word in self._macros

    def _expand_macro_invocation(self, line: str) -> str | None:
        """Expand a macro invocation with parameter substitution.

        Args:
            line: Macro invocation line, e.g., "toupper input, output"

        Returns:
            Expanded macro body with parameters substituted
        """
        stripped = line.strip()
        # Handle optional label prefix
        label = ""
        if ":" in stripped:
            parts = stripped.split(":", 1)
            label = parts[0] + ":"
            stripped = parts[1].strip()

        parts = stripped.split(maxsplit=1)
        if not parts:
            return None

        macro_name = parts[0]
        if macro_name not in self._macros:
            return None

        macro = self._macros[macro_name]
        args_str = parts[1].strip() if len(parts) > 1 else ""
        args = tuple(a.strip() for a in args_str.split(",") if a.strip()) if args_str else ()

        if len(args) != len(macro.parameters):
            # Argument count mismatch - return original line
            return line

        # Substitute parameters in body
        param_map = dict(zip(macro.parameters, args))
        result = []

        for body_line in macro.body:
            expanded_line = body_line
            # Replace \param with actual argument
            for param, arg in param_map.items():
                expanded_line = re.sub(rf'\\{param}\b', arg, expanded_line)
            result.append(expanded_line)

        # Join with label if present
        if label:
            result[0] = label + " " + result[0].lstrip()

        return "\n".join(result)

    def _process_include(self, directive: str, current_file: str) -> str | None:
        """Process .include directive.

        Args:
            directive: The .include line
            current_file: Path of current file for relative paths

        Returns:
            Expanded content from included file, or None if not found
        """
        match = re.match(r'\.include\s+"([^"]+)"', directive, re.IGNORECASE)
        if not match:
            match = re.match(r'\.include\s+<([^>]+)>', directive, re.IGNORECASE)
            if not match:
                return None

        filename = match.group(1)

        # Resolve path relative to current file
        if current_file:
            current_dir = Path(current_file).parent
            include_path = current_dir / filename
        else:
            include_path = Path(filename)

        if not self._source_resolver:
            return None

        content = self._source_resolver(str(include_path))
        if content:
            # Recursively expand included content
            return self.expand(content, str(include_path))

        return None
