"""Tests for the ARM64 instruction set classification."""

from arm64nsd.infrastructure.arm64.instruction_set import (
    MnemonicCategory,
    branch_condition,
    classify_mnemonic,
    is_branch,
    is_conditional_branch,
    is_register,
    is_return,
    negate_condition,
)


class TestClassifyMnemonic:
    def test_add_is_data_processing(self) -> None:
        assert classify_mnemonic("add") == MnemonicCategory.DATA_PROCESSING

    def test_mov_is_data_processing(self) -> None:
        assert classify_mnemonic("mov") == MnemonicCategory.DATA_PROCESSING

    def test_cmp_is_data_processing(self) -> None:
        assert classify_mnemonic("cmp") == MnemonicCategory.DATA_PROCESSING

    def test_ldr_is_load_store(self) -> None:
        assert classify_mnemonic("ldr") == MnemonicCategory.LOAD_STORE

    def test_stp_is_load_store(self) -> None:
        assert classify_mnemonic("stp") == MnemonicCategory.LOAD_STORE

    def test_b_is_branch(self) -> None:
        assert classify_mnemonic("b") == MnemonicCategory.BRANCH

    def test_bl_is_branch(self) -> None:
        assert classify_mnemonic("bl") == MnemonicCategory.BRANCH

    def test_ret_is_branch(self) -> None:
        assert classify_mnemonic("ret") == MnemonicCategory.BRANCH

    def test_b_eq_is_branch(self) -> None:
        assert classify_mnemonic("b.eq") == MnemonicCategory.BRANCH

    def test_b_gt_is_branch(self) -> None:
        assert classify_mnemonic("b.gt") == MnemonicCategory.BRANCH

    def test_cbz_is_branch(self) -> None:
        assert classify_mnemonic("cbz") == MnemonicCategory.BRANCH

    def test_cbnz_is_branch(self) -> None:
        assert classify_mnemonic("cbnz") == MnemonicCategory.BRANCH

    def test_tbz_is_branch(self) -> None:
        assert classify_mnemonic("tbz") == MnemonicCategory.BRANCH

    def test_mul_is_multiply(self) -> None:
        assert classify_mnemonic("mul") == MnemonicCategory.MULTIPLY

    def test_sdiv_is_divide(self) -> None:
        assert classify_mnemonic("sdiv") == MnemonicCategory.DIVIDE

    def test_fadd_is_fp_simd(self) -> None:
        assert classify_mnemonic("fadd") == MnemonicCategory.FP_SIMD

    def test_nop_is_system(self) -> None:
        assert classify_mnemonic("nop") == MnemonicCategory.SYSTEM

    def test_svc_is_system(self) -> None:
        assert classify_mnemonic("svc") == MnemonicCategory.SYSTEM

    def test_csel_is_conditional_select(self) -> None:
        assert classify_mnemonic("csel") == MnemonicCategory.CONDITIONAL_SELECT

    def test_unknown_mnemonic(self) -> None:
        assert classify_mnemonic("xyzzy") == MnemonicCategory.UNKNOWN

    def test_case_insensitive(self) -> None:
        assert classify_mnemonic("ADD") == MnemonicCategory.DATA_PROCESSING
        assert classify_mnemonic("B.EQ") == MnemonicCategory.BRANCH


class TestIsBranch:
    def test_b_is_branch(self) -> None:
        assert is_branch("b") is True

    def test_b_eq_is_branch(self) -> None:
        assert is_branch("b.eq") is True

    def test_add_is_not_branch(self) -> None:
        assert is_branch("add") is False

    def test_cbz_is_branch(self) -> None:
        assert is_branch("cbz") is True


class TestIsConditionalBranch:
    def test_b_eq_is_conditional(self) -> None:
        assert is_conditional_branch("b.eq") is True

    def test_b_is_not_conditional(self) -> None:
        assert is_conditional_branch("b") is False

    def test_cbz_is_conditional(self) -> None:
        assert is_conditional_branch("cbz") is True

    def test_tbnz_is_conditional(self) -> None:
        assert is_conditional_branch("tbnz") is True


class TestIsReturn:
    def test_ret_is_return(self) -> None:
        assert is_return("ret") is True

    def test_bl_is_not_return(self) -> None:
        assert is_return("bl") is False


class TestBranchCondition:
    def test_b_eq_returns_eq(self) -> None:
        assert branch_condition("b.eq") == "eq"

    def test_b_gt_returns_gt(self) -> None:
        assert branch_condition("b.gt") == "gt"

    def test_cbz_returns_eq(self) -> None:
        assert branch_condition("cbz") == "eq"

    def test_cbnz_returns_ne(self) -> None:
        assert branch_condition("cbnz") == "ne"

    def test_b_returns_none(self) -> None:
        assert branch_condition("b") is None


class TestNegateCondition:
    def test_eq_negates_to_ne(self) -> None:
        assert negate_condition("eq") == "ne"

    def test_gt_negates_to_le(self) -> None:
        assert negate_condition("gt") == "le"

    def test_hi_negates_to_ls(self) -> None:
        assert negate_condition("hi") == "ls"


class TestIsRegister:
    def test_x0_is_register(self) -> None:
        assert is_register("x0") is True

    def test_sp_is_register(self) -> None:
        assert is_register("sp") is True

    def test_w0_is_register(self) -> None:
        assert is_register("w0") is True

    def test_v0_is_register(self) -> None:
        assert is_register("v0") is True

    def test_foo_is_not_register(self) -> None:
        assert is_register("foo") is False
