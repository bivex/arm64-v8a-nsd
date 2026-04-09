"""Extract structured control flow from ARM64 assembly."""

from __future__ import annotations

from dataclasses import dataclass

from arm64nsd.domain.control_flow import (
    ActionFlowStep,
    ControlFlowDiagram,
    ControlFlowStep,
    FunctionControlFlow,
)
from arm64nsd.domain.model import SourceUnit
from arm64nsd.domain.ports import Arm64ControlFlowExtractor
from arm64nsd.infrastructure.arm64.branch_analyzer import BranchAnalyzer
from arm64nsd.infrastructure.arm64.instruction_set import is_return
from arm64nsd.infrastructure.arm64.macro_expander import MacroExpander
from arm64nsd.infrastructure.arm64.tokenizer import Arm64Line, Arm64Tokenizer
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FunctionBoundary:
    name: str
    start_line: int   # index into lines tuple (label line)
    end_line: int     # index of ret line (inclusive)
    is_global: bool


class Arm64AsmControlFlowExtractor(Arm64ControlFlowExtractor):
    """Extract structured control flow from ARM64 assembly source."""

    def __init__(self) -> None:
        self._tokenizer = Arm64Tokenizer()
        self._macro_expander = MacroExpander(source_resolver=self._resolve_include_path)

    def _resolve_include_path(self, path: str) -> str | None:
        """Resolve .include path to file content.

        Args:
            path: Path from .include directive

        Returns:
            File content as string, or None if not found
        """
        try:
            include_path = Path(path).expanduser().resolve()
            if include_path.exists():
                return include_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass
        return None

    def extract(self, source_unit: SourceUnit) -> ControlFlowDiagram:
        # Expand macros first
        expanded_content = self._macro_expander.expand(source_unit.content, source_unit.location)
        lines = self._tokenizer.tokenize(expanded_content)
        boundaries = self._detect_function_boundaries(lines)
        functions: list[FunctionControlFlow] = []

        for boundary in boundaries:
            func_lines = lines[boundary.start_line : boundary.end_line + 1]
            steps = self._extract_function_steps(func_lines)
            functions.append(FunctionControlFlow(
                name=boundary.name,
                signature=f"{boundary.name}:",
                container=None,
                steps=steps,
            ))

        # If no functions detected, treat the whole file as one anonymous block
        if not functions and any(line.is_instruction for line in lines):
            steps = self._extract_function_steps(lines)
            if steps:
                functions.append(FunctionControlFlow(
                    name="<module>",
                    signature="<module-level code>",
                    container=None,
                    steps=steps,
                ))

        return ControlFlowDiagram(
            source_location=source_unit.location,
            functions=tuple(functions),
        )

    # ------------------------------------------------------------------
    # Function boundary detection
    # ------------------------------------------------------------------

    def _detect_function_boundaries(self, lines: tuple[Arm64Line, ...]) -> list[FunctionBoundary]:
        # Phase 1: Collect .global names
        global_names: set[str] = set()
        for line in lines:
            if line.directive is not None:
                directive = line.directive.lower()
                if directive in (".global", ".globl"):
                    name = line.operands.strip().split(",")[0].strip()
                    global_names.add(name)

        # Phase 2: Find labels and scan for ret to define function bodies
        boundaries: list[FunctionBoundary] = []

        index = 0
        while index < len(lines):
            line = lines[index]

            # Look for labels
            if line.label is not None and line.label in global_names:
                # This label is a known global — find the matching ret
                end = self._find_function_end(lines, index + 1)
                if end is not None:
                    boundaries.append(FunctionBoundary(
                        name=line.label,
                        start_line=index,
                        end_line=end,
                        is_global=True,
                    ))
                    index = end + 1
                    continue

            # Also detect functions by prologue pattern: label + stp x29, x30
            if line.label is not None and line.label not in global_names:
                # Check if next instruction is a prologue
                next_instr = self._find_next_instruction(lines, index + 1)
                if next_instr is not None:
                    next_line = lines[next_instr]
                    if (next_line.mnemonic is not None
                            and next_line.mnemonic.lower() == "stp"
                            and "x29" in next_line.operands
                            and "x30" in next_line.operands):
                        end = self._find_function_end(lines, next_instr + 1)
                        if end is not None:
                            boundaries.append(FunctionBoundary(
                                name=line.label,
                                start_line=index,
                                end_line=end,
                                is_global=False,
                            ))
                            index = end + 1
                            continue

            index += 1

        return boundaries

    @staticmethod
    def _find_function_end(lines: tuple[Arm64Line, ...], start: int) -> int | None:
        """Find the ret/svc instruction that ends a function."""
        depth = 0
        for index in range(start, len(lines)):
            line = lines[index]
            if line.mnemonic is None:
                continue
            mnem = line.mnemonic.lower()
            # ret or svc (Darwin system call) terminates function
            if (is_return(mnem) or mnem == "svc") and depth == 0:
                return index
            # Handle nested bl/ret patterns — bl doesn't increase depth
            # because ARM64 doesn't have nested function definitions
        return None

    @staticmethod
    def _find_next_instruction(lines: tuple[Arm64Line, ...], start: int) -> int | None:
        """Find the index of the next instruction line at or after start."""
        for index in range(start, len(lines)):
            if lines[index].is_instruction:
                return index
        return None

    # ------------------------------------------------------------------
    # Control flow extraction per function
    # ------------------------------------------------------------------

    def _extract_function_steps(self, lines: tuple[Arm64Line, ...]) -> tuple[ControlFlowStep, ...]:
        if not lines:
            return ()

        # Filter to only instruction lines (skip directives, labels, empty)
        instructions = tuple(line for line in lines if line.is_instruction)

        if not instructions:
            return ()

        # If all instructions are simple (no branches), return as actions
        has_branches = any(
            line.mnemonic is not None and self._is_branch_instruction(line.mnemonic)
            for line in instructions
        )

        if not has_branches:
            steps: list[ControlFlowStep] = []
            for line in instructions:
                if line.mnemonic is not None and not is_return(line.mnemonic):
                    text = line.instruction_text
                    if text.strip():
                        steps.append(ActionFlowStep(label=text))
            return tuple(steps)

        # Has branches — use the branch analyzer
        analyzer = BranchAnalyzer(lines)
        return analyzer.extract_steps()

    @staticmethod
    def _is_branch_instruction(mnemonic: str) -> bool:
        mnem = mnemonic.lower()
        if mnem in ("b", "bl", "br", "blr", "ret", "cbz", "cbnz", "tbz", "tbnz"):
            return True
        if "." in mnem:
            base = mnem.split(".", 1)[0]
            if base == "b":
                return True
        return False
