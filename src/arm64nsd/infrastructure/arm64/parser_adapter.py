"""Hand-written ARM64 assembly parser adapter."""

from __future__ import annotations

from time import perf_counter

from arm64nsd.domain.model import (
    DiagnosticSeverity,
    ParserVersion,
    ParseOutcome,
    ParseStatistics,
    SourceUnit,
    StructuralElement,
    StructuralElementKind,
    SyntaxDiagnostic,
)
from arm64nsd.domain.ports import AssemblySyntaxParser
from arm64nsd.infrastructure.arm64.instruction_set import (
    classify_mnemonic,
    is_directive,
    is_return,
    MnemonicCategory,
)
from arm64nsd.infrastructure.arm64.tokenizer import Arm64Tokenizer


ARM64_PARSER_VERSION = ParserVersion("arm64v8a-handwritten@1.0.0")

_FUNCTION_PROLOGUE_MNEMONICS = {"stp", "sub"}
_FUNCTION_EPILOGUE_MNEMONICS = {"ldp", "add"}
_SECTION_DIRECTIVES = {".text", ".data", ".bss", ".rodata", ".section"}


class Arm64AssemblyParser(AssemblySyntaxParser):
    """Parse ARM64 assembly source and extract structural elements."""

    def __init__(self) -> None:
        self._tokenizer = Arm64Tokenizer()

    @property
    def parser_version(self) -> ParserVersion:
        return ARM64_PARSER_VERSION

    def parse(self, source_unit: SourceUnit) -> ParseOutcome:
        started_at = perf_counter()
        try:
            lines = self._tokenizer.tokenize(source_unit.content)
            diagnostics: list[SyntaxDiagnostic] = []
            elements: list[StructuralElement] = []
            current_section: str | None = None
            current_function: str | None = None

            for line in lines:
                if line.is_empty:
                    continue

                # Section directives
                if line.directive is not None:
                    directive_lower = line.directive.lower()
                    if directive_lower in (".text", ".data", ".bss", ".rodata"):
                        current_section = directive_lower[1:]
                        elements.append(StructuralElement(
                            kind=StructuralElementKind.SECTION,
                            name=current_section,
                            line=line.line_number,
                            column=0,
                            signature=line.raw_text.strip(),
                        ))
                    elif directive_lower in (".global", ".globl"):
                        name = line.operands.strip().split(",")[0].strip()
                        elements.append(StructuralElement(
                            kind=StructuralElementKind.DIRECTIVE,
                            name=name,
                            line=line.line_number,
                            column=0,
                            signature=f".global {name}",
                        ))
                    elif directive_lower == ".type":
                        parts = line.operands.split(",")
                        if len(parts) >= 2 and "@function" in parts[1]:
                            name = parts[0].strip()
                            elements.append(StructuralElement(
                                kind=StructuralElementKind.FUNCTION,
                                name=name,
                                line=line.line_number,
                                column=0,
                                signature=f".type {name}, @function",
                            ))
                    elif directive_lower == ".section":
                        section_name = line.operands.split(",")[0].strip().strip('"')
                        current_section = section_name
                        elements.append(StructuralElement(
                            kind=StructuralElementKind.SECTION,
                            name=section_name,
                            line=line.line_number,
                            column=0,
                            signature=line.raw_text.strip(),
                        ))
                    elif directive_lower in (".macro",):
                        name = line.operands.strip().split()[0].strip() if line.operands.strip() else "anonymous"
                        elements.append(StructuralElement(
                            kind=StructuralElementKind.MACRO,
                            name=name,
                            line=line.line_number,
                            column=0,
                            signature=f".macro {name}",
                        ))
                    elif directive_lower.startswith(".cfi_"):
                        pass  # Skip CFI directives silently
                    else:
                        elements.append(StructuralElement(
                            kind=StructuralElementKind.DIRECTIVE,
                            name=directive_lower,
                            line=line.line_number,
                            column=0,
                            signature=line.raw_text.strip(),
                        ))
                    continue

                # Labels
                if line.label is not None:
                    elements.append(StructuralElement(
                        kind=StructuralElementKind.LABEL,
                        name=line.label,
                        line=line.line_number,
                        column=0,
                        container=current_function,
                    ))
                    # A label followed by a prologue instruction is a function
                    continue

                # Instructions
                if line.mnemonic is not None:
                    mnem = line.mnemonic.lower()
                    category = classify_mnemonic(mnem)

                    if category == MnemonicCategory.LOAD_STORE and mnem == "stp":
                        # Check for function prologue: stp x29, x30, [sp, #...]
                        if "x29" in line.operands and "x30" in line.operands:
                            # Previous label is the function name
                            for elem in reversed(elements):
                                if elem.kind == StructuralElementKind.LABEL:
                                    current_function = elem.name
                                    elements.append(StructuralElement(
                                        kind=StructuralElementKind.FUNCTION,
                                        name=elem.name,
                                        line=line.line_number,
                                        column=0,
                                        container=current_section,
                                        signature=f"{elem.name}: (prologue)",
                                    ))
                                    break

                    if is_return(mnem):
                        current_function = None

            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)
            return ParseOutcome.success(
                source_unit=source_unit,
                parser_version=ARM64_PARSER_VERSION,
                diagnostics=tuple(diagnostics),
                structural_elements=tuple(elements),
                statistics=ParseStatistics(
                    token_count=sum(len(line.tokens) for line in lines) + len(lines),
                    structural_element_count=len(elements),
                    diagnostic_count=len(diagnostics),
                    elapsed_ms=elapsed_ms,
                ),
            )
        except Exception as error:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)
            return ParseOutcome.technical_failure(
                source_unit=source_unit,
                parser_version=ARM64_PARSER_VERSION,
                message=str(error),
                elapsed_ms=elapsed_ms,
            )
