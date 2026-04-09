"""Domain model for structured control flow diagrams."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ControlFlowStep:
    """Base type for a structured control flow step."""


@dataclass(frozen=True, slots=True)
class ActionFlowStep(ControlFlowStep):
    label: str


@dataclass(frozen=True, slots=True)
class CallFlowStep(ControlFlowStep):
    target: str


@dataclass(frozen=True, slots=True)
class TailCallStep(ControlFlowStep):
    target: str


@dataclass(frozen=True, slots=True)
class InlineIfStep(ControlFlowStep):
    """Inline conditional: csel, cset, cinc, cinv, cneg, csinc, csinv, csneg."""
    expression: str


@dataclass(frozen=True, slots=True)
class IndirectBranchStep(ControlFlowStep):
    """Indirect branch via register: br xN (jump table, computed goto)."""
    register: str


@dataclass(frozen=True, slots=True)
class ReturnStep(ControlFlowStep):
    pass


@dataclass(frozen=True, slots=True)
class BreakStep(ControlFlowStep):
    label: str


@dataclass(frozen=True, slots=True)
class ContinueStep(ControlFlowStep):
    label: str


@dataclass(frozen=True, slots=True)
class InfiniteLoopStep(ControlFlowStep):
    pass


@dataclass(frozen=True, slots=True)
class IfFlowStep(ControlFlowStep):
    condition: str
    then_steps: tuple[ControlFlowStep, ...]
    else_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class WhileFlowStep(ControlFlowStep):
    condition: str
    body_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class RepeatWhileFlowStep(ControlFlowStep):
    condition: str
    body_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class SwitchCaseFlow:
    label: str
    steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class SwitchFlowStep(ControlFlowStep):
    expression: str
    cases: tuple[SwitchCaseFlow, ...]


@dataclass(frozen=True, slots=True)
class FunctionControlFlow:
    name: str
    signature: str
    container: str | None
    steps: tuple[ControlFlowStep, ...]

    @property
    def qualified_name(self) -> str:
        if self.container:
            return f"{self.container}.{self.name}"
        return self.name


@dataclass(frozen=True, slots=True)
class ControlFlowDiagram:
    source_location: str
    functions: tuple[FunctionControlFlow, ...]
