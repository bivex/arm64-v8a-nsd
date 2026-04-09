"""Reconstruct structured control flow from ARM64 branch patterns."""

from __future__ import annotations

from dataclasses import dataclass

from arm64nsd.domain.control_flow import (
    ActionFlowStep,
    BreakStep,
    CallFlowStep,
    ContinueStep,
    ControlFlowStep,
    IfFlowStep,
    InfiniteLoopStep,
    RepeatWhileFlowStep,
    ReturnStep,
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

    # Instructions that set flags and precede conditional branches
    _FLAG_SETTING_MNEMONICS = frozenset({
        "cmp", "cmn", "tst", "ands", "bics", "adds", "subs",
    })

    @staticmethod
    def _render_condition(condition_code: str, left: str, right: str) -> str:
        """Render a human-readable condition from code + cmp operands."""
        ops: dict[str, str] = {
            "eq": "==", "ne": "!=",
            "gt": ">",  "lt": "<",
            "ge": ">=", "le": "<=",
            "hi": ">",  "lo": "<",       # unsigned
            "hs": ">=", "ls": "<=",      # unsigned
            "mi": "< 0", "pl": ">= 0",
            "vs": "overflow", "vc": "no overflow",
        }
        op = ops.get(condition_code, condition_code)
        if op in ("< 0", ">= 0", "overflow", "no overflow"):
            return f"{left} {op}"
        return f"{left} {op} {right}"

    def _rich_condition(self, branch_index: int, condition_code: str) -> str:
        """Build a rich condition string by inspecting the flag-setting instruction
        before the branch.  Falls back to the raw condition code.

        *condition_code* may already be negated (e.g. the if-else detector negates
        the branch condition to get the if-condition).  For cbz/cbnz/tbz/tbnz the
        condition_code is compared to the "natural" output of the instruction to
        decide whether to negate the rendered text.
        """
        branch_line = self._lines[branch_index]
        branch_mnem = (branch_line.mnemonic or "").lower()

        # cbz/cbnz — the register is the first operand
        if branch_mnem in ("cbz", "cbnz"):
            parts = [p.strip() for p in branch_line.operands.split(",")]
            reg = parts[0] if parts else "?"
            natural_cond = "eq" if branch_mnem == "cbz" else "ne"
            # If condition_code was negated relative to the natural branch sense,
            # flip the rendered operator.
            if condition_code != natural_cond:
                return f"{reg} != 0" if branch_mnem == "cbz" else f"{reg} == 0"
            return f"{reg} == 0" if branch_mnem == "cbz" else f"{reg} != 0"

        # tbz/tbnz — register and bit are in operands
        if branch_mnem in ("tbz", "tbnz"):
            parts = [p.strip() for p in branch_line.operands.split(",")]
            reg = parts[0] if len(parts) >= 1 else "?"
            bit = parts[1] if len(parts) >= 2 else "?"
            natural_cond = "eq" if branch_mnem == "tbz" else "ne"
            if condition_code != natural_cond:
                return f"{reg}[{bit}] != 0" if branch_mnem == "tbz" else f"{reg}[{bit}] == 0"
            return f"{reg}[{bit}] == 0" if branch_mnem == "tbz" else f"{reg}[{bit}] != 0"

        # b.cond — look for preceding cmp/subs/ands/tst
        for i in range(branch_index - 1, -1, -1):
            line = self._lines[i]
            if not line.is_instruction:
                continue
            mnem = (line.mnemonic or "").lower()
            if mnem in self._FLAG_SETTING_MNEMONICS:
                parts = [p.strip() for p in line.operands.split(",")]
                if mnem == "cmp" and len(parts) == 2:
                    return self._render_condition(condition_code, parts[0], parts[1])
                if mnem == "cmn" and len(parts) == 2:
                    return self._render_condition(condition_code, parts[0], f"-{parts[1]}")
                if mnem == "tst" and len(parts) == 2:
                    return f"{parts[0]} & {parts[1]} != 0" if condition_code != "eq" else f"{parts[0]} & {parts[1]} == 0"
                if mnem in ("adds", "subs") and len(parts) >= 2:
                    return self._render_condition(condition_code, parts[0], parts[1])
                break
            # Stop at other instructions that aren't labels/comments
            if line.mnemonic is not None:
                break
        return condition_code

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
                target_label = self._extract_branch_target(mnem, line.operands)
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
    def _extract_branch_target(mnemonic: str, operands: str) -> str | None:
        """Extract the label target from branch operands.

        For b/b.cond/bl/br/blr the target is the first operand.
        For cbz/cbnz the target is the second operand  (reg, label).
        For tbz/tbnz the target is the third operand   (reg, #bit, label).
        """
        mnem = mnemonic.lower()
        stripped = operands.strip()
        if not stripped:
            return None

        parts = [p.strip() for p in stripped.replace("\t", " ").split(",")]

        if mnem in ("cbz", "cbnz") and len(parts) >= 2:
            candidate = parts[1].strip()
        elif mnem in ("tbz", "tbnz") and len(parts) >= 3:
            candidate = parts[2].strip()
        else:
            candidate = parts[0].strip()

        if candidate and (candidate[0].isalpha() or candidate[0] in ("_", ".")):
            return candidate
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
            raw_cond = branch_condition(branch.mnemonic) or "true"
            if_cond = negate_condition(raw_cond)
            cond = self._rich_condition(branch.line_index, if_cond)

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
                    condition=cond,
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
                    condition=cond,
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

        Recognises pre-condition loops: backward unconditional branch where
        the target has a forward conditional exit inside the body.
        """
        patterns: list[WhileLoopPattern] = []
        used_branches: set[int] = set()

        for branch in self._branches:
            if branch.line_index in used_branches:
                continue
            if branch.is_forward is not False or branch.target_line_index is None:
                continue
            if not is_unconditional_branch(branch.mnemonic):
                continue

            # Backward unconditional branch — look for forward conditional exit
            header_idx = branch.target_line_index
            for other in self._branches:
                if (
                    other.is_conditional
                    and other.is_forward is True
                    and other.line_index > header_idx
                    and other.line_index < branch.line_index
                    and other.line_index not in used_branches
                ):
                    cond = branch_condition(other.mnemonic) or "true"
                    cond = self._rich_condition(other.line_index, cond)
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
        """Detect repeat-until loops: backward conditional branch to body start.

        This handles the common ARM64 pattern where the body executes first,
        then a condition is tested at the bottom:
            label:
              body...
              b.cond label   // repeat while condition holds
        """
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
            cond = self._rich_condition(branch.line_index, cond)

            body_label = None
            for label_name, label_index in self._label_map.items():
                if label_index == branch.target_line_index:
                    body_label = label_name
                    break

            patterns.append(RepeatLoopPattern(
                body_label=body_label,
                body_start=branch.target_line_index,
                body_end=branch.line_index - 1,
                condition_line=branch.line_index,
                branch_line=branch.line_index,
                condition=cond,
            ))
            used_branches.add(branch.line_index)

        return patterns

    def detect_infinite_loops(self) -> list[tuple[int, int]]:
        """Detect infinite loops: backward unconditional branch with no exit.

        Returns list of (header_line, branch_line) pairs.
        An infinite loop is a backward unconditional `b` to a label where
        no forward conditional exit exists between the header and the branch.
        """
        loops: list[tuple[int, int]] = []
        used: set[int] = set()

        for branch in self._branches:
            if branch.line_index in used:
                continue
            if branch.is_conditional or branch.is_forward is not False:
                continue
            if branch.target_line_index is None:
                continue
            if not is_unconditional_branch(branch.mnemonic) or branch.mnemonic.lower() != "b":
                continue

            header = branch.target_line_index
            # Check that NO forward conditional exit exists in the body
            has_exit = any(
                other.is_conditional
                and other.is_forward is True
                and other.line_index > header
                and other.line_index < branch.line_index
                for other in self._branches
            )
            if not has_exit:
                loops.append((header, branch.line_index))
                used.add(branch.line_index)

        return loops
        """Detect repeat-until loops: backward conditional branch to body start.

        This handles the common ARM64 pattern where the body executes first,
        then a condition is tested at the bottom:
            label:
              body...
              b.cond label   // repeat while condition holds
        """
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
            cond = self._rich_condition(branch.line_index, cond)

            body_label = None
            for label_name, label_index in self._label_map.items():
                if label_index == branch.target_line_index:
                    body_label = label_name
                    break

            patterns.append(RepeatLoopPattern(
                body_label=body_label,
                body_start=branch.target_line_index,
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
                    target = self._extract_branch_target(mnem, scan_line.operands)
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
                    target = self._extract_branch_target(mnem, scan_line.operands)
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
        repeat_patterns = self.detect_repeat_loops()
        switch_patterns = self.detect_switch_patterns()
        infinite_loops = self.detect_infinite_loops()

        # Build a map of line ranges covered by structured patterns
        covered: dict[int, str] = {}  # line_index -> pattern_id

        for pat in if_partterns:
            for i in range(pat.condition_line, pat.end_line):
                covered[i] = "if"

        for pat in while_patterns:
            for i in range(pat.header_line, pat.branch_line + 1):
                covered[i] = "while"

        for pat in repeat_patterns:
            for i in range(pat.body_start, pat.branch_line + 1):
                covered[i] = "repeat"

        for pat in switch_patterns:
            for i in range(pat.compare_line, pat.end_line):
                covered[i] = "switch"

        for header, branch in infinite_loops:
            for i in range(header, branch + 1):
                covered[i] = "infinite"

        return self._build_steps(
            start=0,
            end=len(self._lines),
            covered=covered,
            if_patterns=if_partterns,
            while_patterns=while_patterns,
            repeat_patterns=repeat_patterns,
            switch_patterns=switch_patterns,
            infinite_loops=infinite_loops,
        )

    def _build_steps(
        self,
        *,
        start: int,
        end: int,
        covered: dict[int, str],
        if_patterns: list[IfElsePattern],
        while_patterns: list[WhileLoopPattern],
        repeat_patterns: list[RepeatLoopPattern],
        switch_patterns: list[SwitchPattern],
        infinite_loops: list[tuple[int, int]],
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
                    steps.append(self._build_if_step(pat, covered, if_patterns, while_patterns, repeat_patterns, switch_patterns, infinite_loops))
                    index = pat.end_line
                    continue

            if coverage == "while":
                pat = self._find_while_at(index, while_patterns)
                if pat is not None:
                    steps.append(self._build_while_step(pat, covered, if_patterns, while_patterns, repeat_patterns, switch_patterns, infinite_loops))
                    index = pat.branch_line + 1
                    continue

            if coverage == "repeat":
                pat = self._find_repeat_at(index, repeat_patterns)
                if pat is not None:
                    steps.append(self._build_repeat_step(pat, covered, if_patterns, while_patterns, repeat_patterns, switch_patterns, infinite_loops))
                    index = pat.branch_line + 1
                    continue

            if coverage == "switch":
                pat = self._find_switch_at(index, switch_patterns)
                if pat is not None:
                    steps.append(self._build_switch_step(pat, covered, if_patterns, while_patterns, repeat_patterns, switch_patterns, infinite_loops))
                    index = pat.end_line
                    continue

            if coverage == "infinite":
                inf_match = self._find_infinite_at(index, infinite_loops)
                if inf_match is not None:
                    header, branch = inf_match
                    body_steps = self._build_steps(
                        start=header + 1,
                        end=branch,
                        covered=covered,
                        if_patterns=if_patterns,
                        while_patterns=while_patterns,
                        repeat_patterns=repeat_patterns,
                        switch_patterns=switch_patterns,
                        infinite_loops=infinite_loops,
                    )
                    steps.append(InfiniteLoopStep())
                    steps.extend(body_steps)
                    index = branch + 1
                    continue

            # Uncovered line → CallFlowStep, ReturnStep, or ActionFlowStep
            if line.is_instruction:
                mnem = (line.mnemonic or "").lower()
                if is_return(mnem):
                    steps.append(ReturnStep())
                elif mnem in ("bl", "blr"):
                    target = line.operands.strip().split(",")[0].strip() or mnem
                    steps.append(CallFlowStep(target=target))
                else:
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

    def _find_repeat_at(self, index: int, patterns: list[RepeatLoopPattern]) -> RepeatLoopPattern | None:
        for pat in patterns:
            if pat.body_start == index:
                return pat
        return None

    @staticmethod
    def _find_infinite_at(
        index: int, loops: list[tuple[int, int]],
    ) -> tuple[int, int] | None:
        for header, branch in loops:
            if header == index:
                return (header, branch)
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
        repeat_patterns: list[RepeatLoopPattern],
        switch_patterns: list[SwitchPattern],
        infinite_loops: list[tuple[int, int]],
    ) -> IfFlowStep:
        then_steps = self._build_steps(
            start=pat.then_start,
            end=pat.then_end + 1,
            covered=covered,
            if_patterns=if_patterns,
            while_patterns=while_patterns,
            repeat_patterns=repeat_patterns,
            switch_patterns=switch_patterns,
            infinite_loops=infinite_loops,
        )
        else_steps: tuple[ControlFlowStep, ...] = ()
        if pat.else_start is not None and pat.else_end is not None:
            else_steps = self._build_steps(
                start=pat.else_start,
                end=pat.else_end + 1,
                covered=covered,
                if_patterns=if_patterns,
                while_patterns=while_patterns,
                repeat_patterns=repeat_patterns,
                switch_patterns=switch_patterns,
                infinite_loops=infinite_loops,
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
        repeat_patterns: list[RepeatLoopPattern],
        switch_patterns: list[SwitchPattern],
        infinite_loops: list[tuple[int, int]],
    ) -> WhileFlowStep:
        body_steps = self._build_steps(
            start=pat.header_line + 1,  # skip the header label to avoid re-detecting this pattern
            end=pat.body_end + 1,
            covered=covered,
            if_patterns=if_patterns,
            while_patterns=while_patterns,
            repeat_patterns=repeat_patterns,
            switch_patterns=switch_patterns,
            infinite_loops=infinite_loops,
        )
        return WhileFlowStep(
            condition=pat.condition,
            body_steps=body_steps,
        )

    def _build_repeat_step(
        self,
        pat: RepeatLoopPattern,
        covered: dict[int, str],
        if_patterns: list[IfElsePattern],
        while_patterns: list[WhileLoopPattern],
        repeat_patterns: list[RepeatLoopPattern],
        switch_patterns: list[SwitchPattern],
        infinite_loops: list[tuple[int, int]],
    ) -> RepeatWhileFlowStep:
        body_steps = self._build_steps(
            start=pat.body_start + 1,  # skip body start label to avoid re-detecting
            end=pat.body_end + 1,
            covered=covered,
            if_patterns=if_patterns,
            while_patterns=while_patterns,
            repeat_patterns=repeat_patterns,
            switch_patterns=switch_patterns,
            infinite_loops=infinite_loops,
        )
        return RepeatWhileFlowStep(
            condition=pat.condition,
            body_steps=body_steps,
        )

    def _build_switch_step(
        self,
        pat: SwitchPattern,
        covered: dict[int, str],
        if_patterns: list[IfElsePattern],
        while_patterns: list[WhileLoopPattern],
        repeat_patterns: list[RepeatLoopPattern],
        switch_patterns: list[SwitchPattern],
        infinite_loops: list[tuple[int, int]],
    ) -> SwitchFlowStep:
        cases: list[SwitchCaseFlow] = []
        for label, case_start, case_end in pat.cases:
            case_steps = self._build_steps(
                start=case_start,
                end=case_end + 1,
                covered=covered,
                if_patterns=if_patterns,
                while_patterns=while_patterns,
                repeat_patterns=repeat_patterns,
                switch_patterns=switch_patterns,
                infinite_loops=infinite_loops,
            )
            cases.append(SwitchCaseFlow(label=label, steps=case_steps))
        return SwitchFlowStep(
            expression=pat.expression,
            cases=tuple(cases),
        )
