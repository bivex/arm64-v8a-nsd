"""Reconstruct structured control flow from ARM64 branch patterns."""

from __future__ import annotations

from dataclasses import dataclass

from arm64nsd.domain.control_flow import (
    ActionFlowStep,
    ControlFlowStep,
    IfFlowStep,
    RepeatWhileFlowStep,
    SwitchCaseFlow,
    SwitchFlowStep,
    WhileFlowStep,
)
from arm64nsd.infrastructure.arm64.instruction_set import (
    branch_condition,
    is_conditional_branch,
    is_return,
    is_unconditional_branch,
    negate_condition,
)
from arm64nsd.infrastructure.arm64.tokenizer import Arm64Line


# ---------------------------------------------------------------------------
# Branch info
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BranchInfo:
    line_index: int
    mnemonic: str
    target_label: str
    target_line_index: int | None  # None if label is outside this scope
    is_conditional: bool
    is_forward: bool | None  # None if target is unknown


# ---------------------------------------------------------------------------
# Pattern descriptors
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class IfElsePattern:
    """If-else pattern: forward conditional branch over then-body, optional else."""
    condition: str
    condition_line: int
    then_start: int
    then_end: int
    else_start: int | None
    else_end: int | None
    end_line: int
    inverted: bool


@dataclass(frozen=True, slots=True)
class WhileLoopPattern:
    """While loop: backward conditional branch to loop header."""
    header_label: str | None
    header_line: int
    body_start: int
    body_end: int
    condition_line: int
    branch_line: int
    condition: str


@dataclass(frozen=True, slots=True)
class RepeatLoopPattern:
    """Repeat loop: backward conditional branch to loop body start."""
    body_label: str | None
    body_start: int
    body_end: int
    condition_line: int
    branch_line: int
    condition: str


@dataclass(frozen=True, slots=True)
class SwitchPattern:
    """Switch: cascading cmp + b.cond to different forward labels."""
    expression: str
    compare_line: int
    branches_start: int
    branches_end: int
    end_line: int
    cases: tuple[tuple[str, int, int], ...]  # (label, case_start, case_end)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class BranchAnalyzer:
    """Analyze branch patterns in a sequence of ARM64 assembly lines."""

    def __init__(self, lines: tuple[Arm64Line, ...]) -> None:
        self._lines = lines
        self._label_map = self._build_label_map()
        self._branches = self._collect_branches()

    # ------------------------------------------------------------------
    # Map building
    # ------------------------------------------------------------------

    def _label_at(self, line_index: int) -> str | None:
        """Return the label name at *line_index*, if any."""
        for label_name, label_index in self._label_map.items():
            if label_index == line_index:
                return label_name
        return None

    def _build_label_map(self) -> dict[str, int]:
        label_map: dict[str, int] = {}
        for index, line in enumerate(self._lines):
            if line.label is not None:
                label_map[line.label] = index
        return label_map

    def _collect_branches(self) -> tuple[BranchInfo, ...]:
        branches: list[BranchInfo] = []
        for index, line in enumerate(self._lines):
            if line.mnemonic is None:
                continue
            mnem = line.mnemonic.lower()

            if is_conditional_branch(mnem) or is_unconditional_branch(mnem):
                target_label = self._extract_branch_target(line.operands)
                if target_label is None:
                    continue

                target_index = self._label_map.get(target_label)
                is_forward = None
                if target_index is not None:
                    is_forward = target_index > index

                branches.append(BranchInfo(
                    line_index=index,
                    mnemonic=mnem,
                    target_label=target_label,
                    target_line_index=target_index,
                    is_conditional=is_conditional_branch(mnem),
                    is_forward=is_forward,
                ))
        return tuple(branches)

    @staticmethod
    def _extract_branch_target(operands: str) -> str | None:
        """Extract the label target from branch operands."""
        stripped = operands.strip()
        if not stripped:
            return None
        # First token before any comma/space is the target label
        for sep in (",", " ", "\t"):
            if sep in stripped:
                stripped = stripped[:stripped.index(sep)].strip()
                break
        # Clean any remaining whitespace
        stripped = stripped.strip()
        if stripped and stripped[0].isalpha() or stripped[0] in ("_", "."):
            return stripped
        return None

    # ------------------------------------------------------------------
    # Pattern detection
    # ------------------------------------------------------------------

    def detect_if_else_patterns(self) -> list[IfElsePattern]:
        """Detect if-else patterns from forward conditional branches."""
        patterns: list[IfElsePattern] = []
        used_branches: set[int] = set()

        for branch in self._branches:
            if branch.line_index in used_branches:
                continue
            if not branch.is_conditional or branch.is_forward is not True:
                continue
            if branch.target_line_index is None:
                continue

            # Forward conditional branch: this is the "skip then" branch
            # The condition is inverted (branch taken = skip then-body)
            cond = branch_condition(branch.mnemonic) or "true"

            then_start = branch.line_index + 1
            else_label = branch.target_label
            else_start = branch.target_line_index

            # Look for a matching forward unconditional branch at the end of then-body
            # This would be the "skip else" jump
            end_branch: BranchInfo | None = None
            for candidate in self._branches:
                if candidate.line_index <= branch.line_index:
                    continue
                if candidate.line_index >= else_start:
                    break
                if not candidate.is_conditional and is_unconditional_branch(candidate.mnemonic):
                    if candidate.target_line_index is not None and candidate.target_line_index >= else_start:
                        end_branch = candidate
                        break

            if end_branch is not None and end_branch.target_line_index is not None:
                # if-else pattern
                then_end = end_branch.line_index - 1
                end_line = end_branch.target_line_index
                patterns.append(IfElsePattern(
                    condition=negate_condition(cond),
                    condition_line=branch.line_index,
                    then_start=then_start,
                    then_end=then_end,
                    else_start=else_start,
                    else_end=end_line - 1,
                    end_line=end_line,
                    inverted=True,
                ))
                used_branches.add(branch.line_index)
                used_branches.add(end_branch.line_index)
            else:
                # if-only pattern (no else)
                patterns.append(IfElsePattern(
                    condition=negate_condition(cond),
                    condition_line=branch.line_index,
                    then_start=then_start,
                    then_end=else_start - 1,
                    else_start=None,
                    else_end=None,
                    end_line=else_start,
                    inverted=True,
                ))
                used_branches.add(branch.line_index)

        return patterns

    def detect_while_loops(self) -> list[WhileLoopPattern]:
        """Detect while loops from backward branches.

        Two patterns are recognised:
        1. Backward conditional branch (condition at bottom).
        2. Backward unconditional branch where the target has a forward
           conditional exit (condition at top).
        """
        patterns: list[WhileLoopPattern] = []
        used_branches: set[int] = set()

        for branch in self._branches:
            if branch.line_index in used_branches:
                continue
            if branch.is_forward is not False or branch.target_line_index is None:
                continue

            # --- Pattern 1: backward conditional ---
            if branch.is_conditional:
                cond = branch_condition(branch.mnemonic) or "true"
                header_label = self._label_at(branch.target_line_index)
                patterns.append(WhileLoopPattern(
                    header_label=header_label,
                    header_line=branch.target_line_index,
                    body_start=branch.target_line_index,
                    body_end=branch.line_index - 1,
                    condition_line=branch.line_index,
                    branch_line=branch.line_index,
                    condition=cond,
                ))
                used_branches.add(branch.line_index)
                continue

            # --- Pattern 2: backward unconditional with forward conditional exit ---
            if is_unconditional_branch(branch.mnemonic):
                header_idx = branch.target_line_index
                # Scan from header for a forward conditional branch (the loop exit)
                for other in self._branches:
                    if (
                        other.is_conditional
                        and other.is_forward is True
                        and other.line_index > header_idx
                        and other.line_index < branch.line_index
                        and other.line_index not in used_branches
                    ):
                        # The exit condition is on the cmp just before the branch
                        cond = branch_condition(other.mnemonic) or "true"
                        header_label = self._label_at(header_idx)
                        patterns.append(WhileLoopPattern(
                            header_label=header_label,
                            header_line=header_idx,
                            body_start=header_idx,
                            body_end=branch.line_index - 1,
                            condition_line=other.line_index,
                            branch_line=branch.line_index,
                            condition=cond,
                        ))
                        used_branches.add(branch.line_index)
                        used_branches.add(other.line_index)
                        break

        return patterns

    def detect_repeat_loops(self) -> list[RepeatLoopPattern]:
        """Detect repeat-until loops: body + backward conditional branch to body start."""
        patterns: list[RepeatLoopPattern] = []
        used_branches: set[int] = set()

        for branch in self._branches:
            if branch.line_index in used_branches:
                continue
            if not branch.is_conditional or branch.is_forward is not False:
                continue
            if branch.target_line_index is None:
                continue

            cond = branch_condition(branch.mnemonic) or "true"

            body_label = None
            for label_name, label_index in self._label_map.items():
                if label_index == branch.target_line_index:
                    body_label = label_name
                    break

            # Only classify as repeat if branch goes to exactly the body start
            # and there's no loop header separate from the body
            body_start = branch.target_line_index
            if body_start == branch.target_line_index:
                patterns.append(RepeatLoopPattern(
                    body_label=body_label,
                    body_start=body_start,
                    body_end=branch.line_index - 1,
                    condition_line=branch.line_index,
                    branch_line=branch.line_index,
                    condition=cond,
                ))
                used_branches.add(branch.line_index)

        return patterns

    def detect_switch_patterns(self) -> list[SwitchPattern]:
        """Detect switch patterns from cascading cmp + b.cond sequences."""
        patterns: list[SwitchPattern] = []
        index = 0

        while index < len(self._lines):
            line = self._lines[index]
            if line.mnemonic is None or line.mnemonic.lower() != "cmp":
                index += 1
                continue

            # Found cmp — look ahead for cascading b.cond + cmp sequences
            expression = line.operands.strip()
            cascade_start = index
            case_labels: list[tuple[str, str]] = []  # (condition, target_label)

            scan_index = index + 1
            while scan_index < len(self._lines):
                scan_line = self._lines[scan_index]
                if scan_line.mnemonic is None:
                    break

                mnem = scan_line.mnemonic.lower()
                if is_conditional_branch(mnem):
                    target = self._extract_branch_target(scan_line.operands)
                    if target and is_conditional_branch(mnem):
                        cond = branch_condition(mnem) or "eq"
                        case_labels.append((cond, target))
                        scan_index += 1
                        continue
                elif mnem == "cmp":
                    # Another comparison in the cascade
                    scan_index += 1
                    continue
                elif is_unconditional_branch(mnem):
                    # Default case jump
                    target = self._extract_branch_target(scan_line.operands)
                    if target:
                        case_labels.append(("default", target))
                    scan_index += 1
                    break
                else:
                    break
                scan_index += 1

            if len(case_labels) >= 2:
                # Determine end of switch from last case's end
                end_line = scan_index
                cases: list[tuple[str, int, int]] = []

                for cond_label, target in case_labels:
                    target_index = self._label_map.get(target)
                    if target_index is not None:
                        # Case body extends from target label to next case label or end
                        case_end = end_line - 1
                        for other_cond, other_target in case_labels:
                            other_index = self._label_map.get(other_target)
                            if other_index is not None and other_index > target_index:
                                case_end = min(case_end, other_index - 1)
                        cases.append((target, target_index, case_end))

                if cases:
                    patterns.append(SwitchPattern(
                        expression=expression,
                        compare_line=cascade_start,
                        branches_start=cascade_start + 1,
                        branches_end=scan_index,
                        end_line=end_line,
                        cases=tuple(cases),
                    ))
                    index = scan_index
                    continue

            index += 1

        return patterns

    # ------------------------------------------------------------------
    # Main extraction
    # ------------------------------------------------------------------

    def extract_steps(self) -> tuple[ControlFlowStep, ...]:
        """Extract structured control flow steps from the analyzed lines."""
        if_partterns = self.detect_if_else_patterns()
        while_patterns = self.detect_while_loops()
        switch_patterns = self.detect_switch_patterns()

        # Build a map of line ranges covered by structured patterns
        covered: dict[int, str] = {}  # line_index -> pattern_id

        for pat in if_partterns:
            for i in range(pat.condition_line, pat.end_line):
                covered[i] = "if"

        for pat in while_patterns:
            for i in range(pat.header_line, pat.branch_line + 1):
                covered[i] = "while"

        for pat in switch_patterns:
            for i in range(pat.compare_line, pat.end_line):
                covered[i] = "switch"

        return self._build_steps(
            start=0,
            end=len(self._lines),
            covered=covered,
            if_patterns=if_partterns,
            while_patterns=while_patterns,
            switch_patterns=switch_patterns,
        )

    def _build_steps(
        self,
        *,
        start: int,
        end: int,
        covered: dict[int, str],
        if_patterns: list[IfElsePattern],
        while_patterns: list[WhileLoopPattern],
        switch_patterns: list[SwitchPattern],
    ) -> tuple[ControlFlowStep, ...]:
        steps: list[ControlFlowStep] = []
        index = start

        while index < end:
            if index >= len(self._lines):
                break

            line = self._lines[index]
            coverage = covered.get(index)

            if coverage == "if":
                pat = self._find_if_at(index, if_patterns)
                if pat is not None:
                    steps.append(self._build_if_step(pat, covered, if_patterns, while_patterns, switch_patterns))
                    index = pat.end_line
                    continue

            if coverage == "while":
                pat = self._find_while_at(index, while_patterns)
                if pat is not None:
                    steps.append(self._build_while_step(pat, covered, if_patterns, while_patterns, switch_patterns))
                    index = pat.branch_line + 1
                    continue

            if coverage == "switch":
                pat = self._find_switch_at(index, switch_patterns)
                if pat is not None:
                    steps.append(self._build_switch_step(pat, covered, if_patterns, while_patterns, switch_patterns))
                    index = pat.end_line
                    continue

            # Uncovered line → ActionFlowStep
            if line.is_instruction and not is_return(line.mnemonic or ""):
                text = line.instruction_text
                if text.strip():
                    steps.append(ActionFlowStep(label=text))
            elif line.is_directive:
                text = f"{line.directive} {line.operands}".strip()
                if text.strip():
                    steps.append(ActionFlowStep(label=text))

            index += 1

        return tuple(steps)

    def _find_if_at(self, index: int, patterns: list[IfElsePattern]) -> IfElsePattern | None:
        for pat in patterns:
            if pat.condition_line == index:
                return pat
        return None

    def _find_while_at(self, index: int, patterns: list[WhileLoopPattern]) -> WhileLoopPattern | None:
        for pat in patterns:
            if pat.header_line == index:
                return pat
        return None

    def _find_switch_at(self, index: int, patterns: list[SwitchPattern]) -> SwitchPattern | None:
        for pat in patterns:
            if pat.compare_line == index:
                return pat
        return None

    def _build_if_step(
        self,
        pat: IfElsePattern,
        covered: dict[int, str],
        if_patterns: list[IfElsePattern],
        while_patterns: list[WhileLoopPattern],
        switch_patterns: list[SwitchPattern],
    ) -> IfFlowStep:
        then_steps = self._build_steps(
            start=pat.then_start,
            end=pat.then_end + 1,
            covered=covered,
            if_patterns=if_patterns,
            while_patterns=while_patterns,
            switch_patterns=switch_patterns,
        )
        else_steps: tuple[ControlFlowStep, ...] = ()
        if pat.else_start is not None and pat.else_end is not None:
            else_steps = self._build_steps(
                start=pat.else_start,
                end=pat.else_end + 1,
                covered=covered,
                if_patterns=if_patterns,
                while_patterns=while_patterns,
                switch_patterns=switch_patterns,
            )
        return IfFlowStep(
            condition=pat.condition,
            then_steps=then_steps,
            else_steps=else_steps,
        )

    def _build_while_step(
        self,
        pat: WhileLoopPattern,
        covered: dict[int, str],
        if_patterns: list[IfElsePattern],
        while_patterns: list[WhileLoopPattern],
        switch_patterns: list[SwitchPattern],
    ) -> WhileFlowStep:
        body_steps = self._build_steps(
            start=pat.header_line + 1,  # skip the header label to avoid re-detecting this pattern
            end=pat.body_end + 1,
            covered=covered,
            if_patterns=if_patterns,
            while_patterns=while_patterns,
            switch_patterns=switch_patterns,
        )
        return WhileFlowStep(
            condition=pat.condition,
            body_steps=body_steps,
        )

    def _build_switch_step(
        self,
        pat: SwitchPattern,
        covered: dict[int, str],
        if_patterns: list[IfElsePattern],
        while_patterns: list[WhileLoopPattern],
        switch_patterns: list[SwitchPattern],
    ) -> SwitchFlowStep:
        cases: list[SwitchCaseFlow] = []
        for label, case_start, case_end in pat.cases:
            case_steps = self._build_steps(
                start=case_start,
                end=case_end + 1,
                covered=covered,
                if_patterns=if_patterns,
                while_patterns=while_patterns,
                switch_patterns=switch_patterns,
            )
            cases.append(SwitchCaseFlow(label=label, steps=case_steps))
        return SwitchFlowStep(
            expression=pat.expression,
            cases=tuple(cases),
        )
