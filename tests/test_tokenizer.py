"""Tests for the ARM64 assembly tokenizer."""

from arm64nsd.infrastructure.arm64.tokenizer import Arm64Tokenizer


def test_tokenize_simple_function() -> None:
    source = """\
    .text
    .global _main

_main:
    mov x0, #0
    add x0, x0, #1
    ret
"""
    tokenizer = Arm64Tokenizer()
    lines = tokenizer.tokenize(source)

    # .text, .global _main, empty, _main:, mov, add, ret = 7 lines
    assert len(lines) == 7

    # Check .text directive
    assert lines[0].directive == ".text"
    assert lines[0].is_directive

    # Check .global directive
    assert lines[1].directive == ".global"
    assert lines[1].operands.strip() == "_main"

    # Check label
    assert lines[3].label == "_main"
    assert lines[3].mnemonic is None

    # Check instructions
    assert lines[4].mnemonic == "mov"
    assert lines[4].operands.strip() == "x0, #0"
    assert lines[4].is_instruction

    assert lines[5].mnemonic == "add"
    assert lines[6].mnemonic == "ret"


def test_tokenize_strips_comments() -> None:
    source = "mov x0, #1  // set x0 to 1"
    tokenizer = Arm64Tokenizer()
    lines = tokenizer.tokenize(source)

    assert len(lines) == 1
    assert lines[0].mnemonic == "mov"
    assert lines[0].comment is not None
    assert "//" in lines[0].comment


def test_tokenize_label_on_same_line_as_instruction() -> None:
    source = "loop: add x0, x0, #1"
    tokenizer = Arm64Tokenizer()
    lines = tokenizer.tokenize(source)

    assert len(lines) == 1
    assert lines[0].label == "loop"
    assert lines[0].mnemonic == "add"


def test_tokenize_conditional_branch() -> None:
    source = "b.eq _label"
    tokenizer = Arm64Tokenizer()
    lines = tokenizer.tokenize(source)

    assert len(lines) == 1
    assert lines[0].mnemonic == "b.eq"
    assert lines[0].operands.strip() == "_label"


def test_tokenize_empty_lines() -> None:
    source = "\n\n\n"
    tokenizer = Arm64Tokenizer()
    lines = tokenizer.tokenize(source)

    assert len(lines) == 3
    assert all(line.is_empty for line in lines)


def test_tokenize_operands_brackets() -> None:
    source = "ldr x0, [sp, #16]"
    tokenizer = Arm64Tokenizer()
    lines = tokenizer.tokenize(source)

    assert len(lines) == 1
    assert lines[0].mnemonic == "ldr"
    text = lines[0].instruction_text
    assert "ldr x0, [sp, #16]" == text
