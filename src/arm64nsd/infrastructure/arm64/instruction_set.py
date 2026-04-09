"""ARM64/AArch64 instruction set vocabulary for arm64-v8a."""

from __future__ import annotations

from enum import StrEnum


# ---------------------------------------------------------------------------
# Instruction categories
# ---------------------------------------------------------------------------

class MnemonicCategory(StrEnum):
    DATA_PROCESSING = "data_processing"
    LOAD_STORE = "load_store"
    BRANCH = "branch"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    FP_SIMD = "fp_simd"
    SYSTEM = "system"
    CONDITIONAL_SELECT = "conditional_select"
    BITFIELD = "bitfield"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data processing – integer
# ---------------------------------------------------------------------------

DATA_PROCESSING_MNEMONICS: frozenset[str] = frozenset({
    # Move
    "mov", "movz", "movn", "movk",
    # Arithmetic
    "add", "adds", "sub", "subs", "adc", "adcs", "sbc", "sbcs",
    "neg", "negs",
    # Logical
    "and", "ands", "orr", "orn", "eor", "eon", "bic", "bics", "tst", "mvn",
    # Shift / bit operations
    "lsl", "lsr", "asr", "ror",
    "ubfm", "sbfm", "bfm", "ubfx", "sbfx", "bfi", "bfxil",
    "rbit", "rev", "rev16", "rev32", "clz", "cls",
    # Compare
    "cmp", "cmn",
    # Address computation
    "adr", "adrp",
    # Extend
    "sxtb", "sxth", "sxtw", "uxtb", "uxth",
})


MULTIPLY_MNEMONICS: frozenset[str] = frozenset({
    "mul", "madd", "msub",
    "smull", "umull", "smaddl", "umaddl", "smsubl", "umsubl",
    "smulh", "umulh",
})


DIVIDE_MNEMONICS: frozenset[str] = frozenset({
    "sdiv", "udiv",
})


# ---------------------------------------------------------------------------
# Load / Store
# ---------------------------------------------------------------------------

LOAD_STORE_MNEMONICS: frozenset[str] = frozenset({
    # Integer loads/stores
    "ldr", "str", "ldrb", "strb", "ldrh", "strh",
    "ldrsb", "ldrsh", "ldrsw",
    "ldp", "stp", "ldnp", "stnp",
    "ldur", "stur", "ldurb", "sturb", "ldurh", "sturh",
    "ldursb", "ldursh", "ldursw",
    # Exclusive / atomic
    "ldxr", "stxr", "ldaxr", "stlxr", "ldxp", "stxp",
    "cas", "casa", "casl", "casal",
    "ldadd", "stadd", "swp",
})


# ---------------------------------------------------------------------------
# Branch
# ---------------------------------------------------------------------------

UNCONDITIONAL_BRANCH_MNEMONICS: frozenset[str] = frozenset({
    "b", "bl", "br", "blr", "ret",
})

COMPARE_AND_BRANCH_MNEMONICS: frozenset[str] = frozenset({
    "cbz", "cbnz",
})

TEST_AND_BRANCH_MNEMONICS: frozenset[str] = frozenset({
    "tbz", "tbnz",
})

CONDITION_CODES: frozenset[str] = frozenset({
    "eq", "ne", "cs", "hs", "cc", "lo", "mi", "pl",
    "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le", "al", "nv",
})

CONDITION_CODE_ALIASES: dict[str, str] = {
    "cs": "hs",
    "cc": "lo",
}


# ---------------------------------------------------------------------------
# Conditional select
# ---------------------------------------------------------------------------

CONDITIONAL_SELECT_MNEMONICS: frozenset[str] = frozenset({
    "csel", "csinc", "csinv", "csneg",
    "cset", "csetm", "cinc", "cinv", "cneg",
})


# ---------------------------------------------------------------------------
# FP / SIMD (NEON)
# ---------------------------------------------------------------------------

FP_SIMD_MNEMONICS: frozenset[str] = frozenset({
    # Scalar FP
    "fmov", "fadd", "fsub", "fmul", "fdiv", "fabs", "fneg", "fsqrt",
    "fcmp", "fcmpe", "fcsel", "fcvt",
    "fcvtzs", "fcvtzu", "scvtf", "ucvtf",
    "frintn", "frintm", "frintp", "frintz",
    # NEON vector
    "dup", "ins", "umov", "smov", "movi",
    "mla", "mls", "fmla", "fmls",
    "ext", "tbl", "zip1", "zip2", "uzp1", "uzp2", "trn1", "trn2",
    "shl", "sshr", "ushr",
    "sqadd", "uqadd", "sqsub", "uqsub",
    "smax", "umax", "smin", "umin",
    "cmeq", "cmgt", "cmge", "fcmeq", "fcmgt", "fcmge",
})


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

SYSTEM_MNEMONICS: frozenset[str] = frozenset({
    "svc", "hvc", "smc", "brk", "hlt", "nop",
    "yield", "wfe", "wfi", "sev", "sevl",
    "isb", "dsb", "dmb", "mrs", "msr",
    "sys", "at", "tlbi", "ic", "dc", "prfm",
})


# ---------------------------------------------------------------------------
# Bitfield
# ---------------------------------------------------------------------------

BITFIELD_MNEMONICS: frozenset[str] = frozenset({
    "ubfm", "sbfm", "bfm", "ubfx", "sbfx", "bfi", "bfxil",
})


# ---------------------------------------------------------------------------
# Registers
# ---------------------------------------------------------------------------

GENERAL_PURPOSE_64: frozenset[str] = frozenset(
    {f"x{i}" for i in range(31)} | {"sp", "xzr", "lr", "fp"}
)

GENERAL_PURPOSE_32: frozenset[str] = frozenset(
    {f"w{i}" for i in range(31)} | {"wsp", "wzr"}
)

SIMD_FP_VIEWS: frozenset[str] = frozenset(
    {prefix + str(i) for prefix in ("v", "b", "h", "s", "d", "q") for i in range(32)}
)

ALL_REGISTERS: frozenset[str] = GENERAL_PURPOSE_64 | GENERAL_PURPOSE_32 | SIMD_FP_VIEWS


# ---------------------------------------------------------------------------
# Directives (GAS / Clang)
# ---------------------------------------------------------------------------

DIRECTIVES: frozenset[str] = frozenset({
    "text", "data", "bss", "rodata",
    "global", "globl", "local",
    "type", "size", "align", "balign", "p2align",
    "byte", "2byte", "4byte", "8byte", "word", "long", "quad",
    "asciz", "ascii", "skip", "space", "zero", "comm",
    "section", "pushsection", "popsection",
    "file", "loc", "ident",
    "macro", "endm", "exitm",
    "irp", "irpc", "rept", "endr",
    "ifdef", "ifndef", "if", "else", "endif",
    "equiv", "eqv", "set",
    "include",
    "previous",
    "fnstart", "fnend", "cantunwind", "handlerdata",
    "save", "pad",
    "arch", "cpu",
    "cfi_startproc", "cfi_endproc", "cfi_def_cfa", "cfi_def_cfa_offset",
    "cfi_offset", "cfi_restore", "cfi_adjust_cfa_offset",
    "cfi_rel_offset", "cfi_undefined", "cfi_same_value",
    "cfi_register", "cfi_window_save", "cfi_return_column",
    "cfi_signal_frame", "cfi_lsda", "cfi_escape",
    "thumb_set", "arm", "thumb", "code", "thumb_func",
    "ltorg", "pool",
    "req", "unreq",
    "extern",
})


# ---------------------------------------------------------------------------
# Extend / shift modifiers (used in operands)
# ---------------------------------------------------------------------------

EXTEND_MODIFIERS: frozenset[str] = frozenset({
    "uxtb", "uxth", "uxtw", "uxtx",
    "sxtb", "sxth", "sxtw", "sxtx",
})

SHIFT_MODIFIERS: frozenset[str] = frozenset({
    "lsl", "lsr", "asr", "ror",
})


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def classify_mnemonic(mnemonic: str) -> MnemonicCategory:
    """Return the instruction category for *mnemonic*."""
    low = mnemonic.lower()

    # Strip optional condition-code suffix for branches (e.g. "b.eq")
    if low == "ret":
        return MnemonicCategory.BRANCH
    if low in ("b", "br", "blr", "bl"):
        return MnemonicCategory.BRANCH
    if "." in low:
        base, suffix = low.split(".", 1)
        if base == "b" and suffix in CONDITION_CODES:
            return MnemonicCategory.BRANCH
        if base == "ret":
            return MnemonicCategory.BRANCH

    if low in UNCONDITIONAL_BRANCH_MNEMONICS:
        return MnemonicCategory.BRANCH
    if low in COMPARE_AND_BRANCH_MNEMONICS:
        return MnemonicCategory.BRANCH
    if low in TEST_AND_BRANCH_MNEMONICS:
        return MnemonicCategory.BRANCH
    if low in CONDITIONAL_SELECT_MNEMONICS:
        return MnemonicCategory.CONDITIONAL_SELECT
    if low in DATA_PROCESSING_MNEMONICS:
        return MnemonicCategory.DATA_PROCESSING
    if low in LOAD_STORE_MNEMONICS:
        return MnemonicCategory.LOAD_STORE
    if low in MULTIPLY_MNEMONICS:
        return MnemonicCategory.MULTIPLY
    if low in DIVIDE_MNEMONICS:
        return MnemonicCategory.DIVIDE
    if low in FP_SIMD_MNEMONICS:
        return MnemonicCategory.FP_SIMD
    if low in SYSTEM_MNEMONICS:
        return MnemonicCategory.SYSTEM
    if low in BITFIELD_MNEMONICS:
        return MnemonicCategory.BITFIELD
    return MnemonicCategory.UNKNOWN


def is_branch(mnemonic: str) -> bool:
    """True when *mnemonic* is any kind of branch (conditional or not)."""
    return classify_mnemonic(mnemonic) == MnemonicCategory.BRANCH


def is_unconditional_branch(mnemonic: str) -> bool:
    """True when *mnemonic* is an unconditional branch (b, bl, br, blr, ret)."""
    low = mnemonic.lower()
    if low in ("b", "bl", "br", "blr", "ret"):
        return True
    return False


def is_conditional_branch(mnemonic: str) -> bool:
    """True when *mnemonic* is a conditional branch (b.cond, cbz, cbnz, tbz, tbnz)."""
    low = mnemonic.lower()
    if low in COMPARE_AND_BRANCH_MNEMONICS:
        return True
    if low in TEST_AND_BRANCH_MNEMONICS:
        return True
    if "." in low:
        base, suffix = low.split(".", 1)
        if base == "b" and suffix in CONDITION_CODES:
            return True
    return False


def is_return(mnemonic: str) -> bool:
    """True when *mnemonic* is ``ret``."""
    return mnemonic.lower() == "ret"


def branch_condition(mnemonic: str) -> str | None:
    """Return the condition code for a conditional branch, or None."""
    low = mnemonic.lower()
    if low in COMPARE_AND_BRANCH_MNEMONICS:
        return "ne" if low == "cbnz" else "eq"
    if low in TEST_AND_BRANCH_MNEMONICS:
        return "ne" if low == "tbnz" else "eq"
    if "." in low:
        base, suffix = low.split(".", 1)
        if base == "b" and suffix in CONDITION_CODES:
            return suffix
    return None


def negate_condition(condition: str) -> str:
    """Return the logically negated condition code."""
    negation_map = {
        "eq": "ne", "ne": "eq",
        "gt": "le", "le": "gt",
        "gt": "le", "lt": "ge", "ge": "lt",
        "hi": "ls", "ls": "hi",
        "hs": "lo", "lo": "hs",
        "cs": "cc", "cc": "cs",
        "mi": "pl", "pl": "mi",
        "vs": "vc", "vc": "vs",
        "al": "nv", "nv": "al",
    }
    return negation_map.get(condition, condition)


def is_register(token: str) -> bool:
    """True when *token* looks like a known register name."""
    return token.lower().strip() in ALL_REGISTERS


# ---------------------------------------------------------------------------
# Stack frame helpers
# ---------------------------------------------------------------------------

_STACK_FRAME_REGISTERS: frozenset[str] = frozenset({"fp", "lr", "x29", "x30"})


def is_prologue_instruction(mnemonic: str, operands: str) -> bool:
    """True when the instruction is a typical function prologue operation.

    Recognised patterns:
      - stp x29, x30, [sp, #... ]!   (push frame record)
      - stp fp, lr, [sp, #...]!
      - sub sp, sp, #N               (allocate stack frame)
      - mov x29, sp                  (set frame pointer)
      - mov fp, sp
      - add x29, sp, #0
    """
    mnem = mnemonic.lower()
    ops = operands.lower().replace(" ", "")

    # stp with fp/lr/x29/x30 targeting [sp, ...]!
    if mnem == "stp":
        has_frame_reg = any(r in ops for r in _STACK_FRAME_REGISTERS)
        has_sp = "sp" in ops and ("[sp" in ops or ",sp" in ops)
        return has_frame_reg and has_sp

    # sub sp, sp, #N or sub sp, sp, N
    if mnem == "sub":
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) >= 2 and parts[0].strip().lower() == "sp" and parts[1].strip().lower() == "sp":
            return True

    # mov x29, sp / mov fp, sp / add x29, sp, #0
    if mnem == "mov":
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) >= 2 and parts[0].strip().lower() in ("x29", "fp") and parts[1].strip().lower() == "sp":
            return True

    if mnem == "add":
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) >= 2 and parts[0].strip().lower() in ("x29", "fp") and parts[1].strip().lower() == "sp":
            return True

    return False


def is_epilogue_instruction(mnemonic: str, operands: str) -> bool:
    """True when the instruction is a typical function epilogue operation.

    Recognised patterns:
      - ldp x29, x30, [sp], #N      (pop frame record)
      - ldp fp, lr, [sp], #N
      - add sp, sp, #N               (deallocate stack frame)
      - mov sp, x29 / mov sp, fp     (restore sp from frame pointer)
    """
    mnem = mnemonic.lower()
    ops = operands.lower().replace(" ", "")

    # ldp with fp/lr/x29/x30 from [sp], #N
    if mnem == "ldp":
        has_frame_reg = any(r in ops for r in _STACK_FRAME_REGISTERS)
        has_sp = "sp" in ops and ("[sp" in ops or ",sp" in ops)
        return has_frame_reg and has_sp

    # add sp, sp, #N
    if mnem in ("add", "mov"):
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) >= 2 and parts[0].strip().lower() == "sp":
            src = parts[1].strip().lower()
            if mnem == "mov" and src in ("x29", "fp"):
                return True
            if mnem == "add" and src == "sp":
                return True

    return False


def is_directive(token: str) -> bool:
    """True when *token* starts with ``.`` and matches a known directive name."""
    if not token.startswith("."):
        return False
    return token[1:].lower() in DIRECTIVES
