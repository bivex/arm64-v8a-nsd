"""Regex-based line tokenizer for ARM64 assembly (GAS/Clang syntax)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TokenKind:
    REGISTER = "register"
    IMMEDIATE = "immediate"
    IDENTIFIER = "identifier"
    COMMA = "comma"
    LBRACKET = "lbracket"
    RBRACKET = "rbracket"
    HASH = "hash"
    EXCLAIM = "exclaim"
    PLUS = "plus"
    MINUS = "minus"
    COLON = "colon"
    STRING = "string"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Arm64Token:
    kind: str
    text: str
    column: int


# ---------------------------------------------------------------------------
# Parsed line
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Arm64Line:
    line_number: int
    raw_text: str
    label: str | None
    mnemonic: str | None
    directive: str | None
    operands: str
    comment: str | None
    tokens: tuple[Arm64Token, ...] = ()

    @property
    def is_empty(self) -> bool:
        return (
            self.label is None
            and self.mnemonic is None
            and self.directive is None
            and not self.operands.strip()
        )

    @property
    def is_instruction(self) -> bool:
        return self.mnemonic is not None

    @property
    def is_directive(self) -> bool:
        return self.directive is not None

    @property
    def instruction_text(self) -> str:
        """Reconstruct the full instruction text (mnemonic + operands)."""
        if self.mnemonic is None:
            return ""
        if self.operands.strip():
            return f"{self.mnemonic} {self.operands.strip()}"
        return self.mnemonic


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_COMMENT_RE = re.compile(r"//.*$|/\*.*?\*/", re.DOTALL)
_LABEL_RE = re.compile(r"^\s*([A-Za-z_.]\w*)\s*:")
_DIRECTIVE_RE = re.compile(r"^\s*(\.[A-Za-z_]\w*)\b")
_MNEMONIC_RE = re.compile(r"^\s*([A-Za-z][\w.]*)(?:\s|$)")

# Operand-level token patterns
_OPERAND_TOKEN_RE = re.compile(
    r"""
    (?P<STRING>"[^"]*"|'[^']*')                     |  # string literal
    (?P<LBRACKET>\[)                                 |
    (?P<RBRACKET>\])                                 |
    (?P<EXCLAIM>!)                                   |
    (?P<COMMA>,)                                     |
    (?P<HASH>\#)                                     |
    (?P<PLUS>\+)                                     |
    (?P<MINUS>-)                                     |
    (?P<HEXIMM>0[xX][0-9a-fA-F]+)                   |  # hex immediate (before identifier)
    (?P<IMMEDIATE>\d+)                               |  # decimal immediate
    (?P<IDENTIFIER>[A-Za-z_.\$][\w.\$]*)             |  # identifier/register
    (?P<UNKNOWN>\S)                                     # single unknown char
    """,
    re.VERBOSE,
)


class Arm64Tokenizer:
    """Regex-based line tokenizer for ARM64 assembly source."""

    def tokenize(self, source: str) -> tuple[Arm64Line, ...]:
        raw_lines = source.splitlines()
        joined = self._join_continuation_lines(raw_lines)
        return tuple(self._parse_line(line_number, text) for line_number, text in joined)

    # ------------------------------------------------------------------
    # Line joining (backslash continuation)
    # ------------------------------------------------------------------

    @staticmethod
    def _join_continuation_lines(raw_lines: list[str]) -> list[tuple[int, str]]:
        result: list[tuple[int, str]] = []
        buffer: list[str] = []
        first_line_number: int = 0

        for index, raw in enumerate(raw_lines):
            stripped = raw.rstrip()
            if stripped.endswith("\\"):
                if not buffer:
                    first_line_number = index + 1
                buffer.append(stripped[:-1])
            else:
                if buffer:
                    buffer.append(stripped)
                    result.append((first_line_number, " ".join(buffer)))
                    buffer = []
                else:
                    result.append((index + 1, raw))

        if buffer:
            result.append((first_line_number, " ".join(buffer)))

        return result

    # ------------------------------------------------------------------
    # Line parsing
    # ------------------------------------------------------------------

    def _parse_line(self, line_number: int, raw: str) -> Arm64Line:
        # Strip comments
        comment: str | None = None
        code = _COMMENT_RE.sub("", raw)
        comment_match = _COMMENT_RE.search(raw)
        if comment_match:
            comment = raw[comment_match.start():].strip()

        code = code.strip()
        if not code:
            return Arm64Line(
                line_number=line_number,
                raw_text=raw,
                label=None,
                mnemonic=None,
                directive=None,
                operands="",
                comment=comment,
            )

        # Try label
        label_match = _LABEL_RE.match(code)
        label: str | None = None
        if label_match:
            label = label_match.group(1)
            code = code[label_match.end():].strip()

        if not code:
            return Arm64Line(
                line_number=line_number,
                raw_text=raw,
                label=label,
                mnemonic=None,
                directive=None,
                operands="",
                comment=comment,
            )

        # Try directive
        directive: str | None = None
        directive_match = _DIRECTIVE_RE.match(code)
        if directive_match:
            directive = directive_match.group(1).lower()
            operands = code[directive_match.end():].strip()
            return Arm64Line(
                line_number=line_number,
                raw_text=raw,
                label=label,
                mnemonic=None,
                directive=directive,
                operands=operands,
                comment=comment,
            )

        # Try instruction mnemonic
        mnemonic: str | None = None
        mnemonic_match = _MNEMONIC_RE.match(code)
        if mnemonic_match:
            mnemonic = mnemonic_match.group(1).lower()
            operands = code[mnemonic_match.end():].strip()
        else:
            operands = code

        # Tokenize operands
        tokens = self._tokenize_operands(operands) if operands.strip() else ()

        return Arm64Line(
            line_number=line_number,
            raw_text=raw,
            label=label,
            mnemonic=mnemonic,
            directive=None,
            operands=operands,
            comment=comment,
            tokens=tokens,
        )

    # ------------------------------------------------------------------
    # Operand tokenization
    # ------------------------------------------------------------------

    def _tokenize_operands(self, operand_str: str) -> tuple[Arm64Token, ...]:
        tokens: list[Arm64Token] = []
        for match in _OPERAND_TOKEN_RE.finditer(operand_str):
            kind = match.lastgroup
            text = match.group()
            col = match.start()

            if kind == "HEXIMM":
                kind = TokenKind.IMMEDIATE
            elif kind == "STRING":
                kind = TokenKind.STRING

            tokens.append(Arm64Token(kind=kind or TokenKind.UNKNOWN, text=text, column=col))

        return tuple(tokens)
