// =============================================================================
// ARM64 v8-A Demo — Comprehensive Feature Showcase
// Target: AArch64 arm64-v8a (GAS / Clang integrated assembler syntax)
// =============================================================================
//
// This file exercises every control-flow structure that the arm64nsd
// Nassi-Shneiderman diagram generator can recognise:
//
//   - Multiple functions with standard prologue/epilogue
//   - Linear sequences of data-processing, load/store, and FP/SIMD instructions
//   - if / else  (forward conditional branch + matching forward unconditional)
//   - if-only    (forward conditional branch, no else clause)
//   - while loop (backward unconditional branch with forward conditional exit)
//   - nested if-inside-while
//   - switch     (cascading cmp + b.cond dispatch table)
//   - repeat     (backward conditional branch to body start)
//   - Various addressing modes, register classes, and directives
//
// Assemble:  as -o demo.o demo_arm64v8a.asm
// =============================================================================

    .section __TEXT, __text, regular, pure_instructions
    .align 4

// ─────────────────────────────────────────────────────────────────────────────
// Function: _abs_diff
//   Returns |x0 - x1| in x0.  Demonstrates: if-else.
// ─────────────────────────────────────────────────────────────────────────────
    .global _abs_diff
    .type _abs_diff, @function

_abs_diff:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    sub x2, x0, x1          // x2 = x0 - x1
    cmp x2, #0
    b.lt _abs_diff_else      // if x2 < 0, go to else

    // then: difference is already positive
    mov x0, x2
    b _abs_diff_end

_abs_diff_else:
    neg x0, x2              // x0 = -(x2)

_abs_diff_end:
    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Function: _sum_to_n
//   Computes 1 + 2 + ... + x0 using a while loop.
//   Demonstrates: while loop (backward unconditional branch + forward exit).
// ─────────────────────────────────────────────────────────────────────────────
    .global _sum_to_n
    .type _sum_to_n, @function

_sum_to_n:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x1, #0              // accumulator = 0
    mov x2, #1              // counter = 1

_sum_to_n_loop:
    cmp x2, x0
    b.gt _sum_to_n_done     // while counter <= n
    add x1, x1, x2          // acc += counter
    add x2, x2, #1          // counter++
    b _sum_to_n_loop

_sum_to_n_done:
    mov x0, x1              // return accumulator
    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Function: _count_bits
//   Population count for x0.  Demonstrates: while loop (backward conditional).
// ─────────────────────────────────────────────────────────────────────────────
    .global _count_bits
    .type _count_bits, @function

_count_bits:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x1, #0              // bit count = 0

_count_bits_loop:
    cbz x0, _count_bits_done  // while x0 != 0
    and x2, x0, #1          // x2 = x0 & 1
    add x1, x1, x2          // count += bit
    lsr x0, x0, #1          // x0 >>= 1
    b _count_bits_loop

_count_bits_done:
    mov x0, x1
    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Function: _clamp
//   Clamps x0 to [x1, x2].  Demonstrates: if-only (no else), two in sequence.
// ─────────────────────────────────────────────────────────────────────────────
    .global _clamp
    .type _clamp, @function

_clamp:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    // if x0 < lo, clamp up
    cmp x0, x1
    b.ge _clamp_check_hi
    mov x0, x1

_clamp_check_hi:
    // if x0 > hi, clamp down
    cmp x0, x2
    b.le _clamp_done
    mov x0, x2

_clamp_done:
    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Function: _classify
//   Returns 0/1/2/3 based on x0 value.  Demonstrates: switch (cascading cmp+b.cond).
// ─────────────────────────────────────────────────────────────────────────────
    .global _classify
    .type _classify, @function

_classify:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    cmp x0, #0
    b.eq _classify_zero
    cmp x0, #1
    b.eq _classify_one
    cmp x0, #2
    b.eq _classify_two
    b _classify_default

_classify_zero:
    mov x0, #0
    b _classify_end

_classify_one:
    mov x0, #1
    b _classify_end

_classify_two:
    mov x0, #2
    b _classify_end

_classify_default:
    mvn x0, xzr             // x0 = -1 (all bits set)

_classify_end:
    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Function: _filter_range
//   Counts how many of x3 elements in array [x0] fall in range [x1, x2].
//   Demonstrates: nested if-inside-while, load/store, various addressing modes.
// ─────────────────────────────────────────────────────────────────────────────
    .global _filter_range
    .type _filter_range, @function

_filter_range:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x4, #0              // matched count = 0
    mov x5, #0              // index = 0

_filter_range_loop:
    cmp x5, x3
    b.ge _filter_range_done // while index < length

    ldr x6, [x0, x5, lsl #3]  // x6 = array[index] (8-byte elements)
    cmp x6, x1
    b.lt _filter_range_next    // if value < lo, skip

    cmp x6, x2
    b.gt _filter_range_next    // if value > hi, skip

    add x4, x4, #1             // matched++

_filter_range_next:
    add x5, x5, #1             // index++
    b _filter_range_loop

_filter_range_done:
    mov x0, x4
    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Function: _delay_cycles
//   Busy-wait loop (repeat-until).  Demonstrates: repeat pattern.
// ─────────────────────────────────────────────────────────────────────────────
    .global _delay_cycles
    .type _delay_cycles, @function

_delay_cycles:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

_delay_cycles_repeat:
    sub x0, x0, #1          // cycles--
    cmp x0, #0
    b.gt _delay_cycles_repeat  // repeat until cycles <= 0

    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Function: _vector_dot
//   Computes dot product of two [x0] and [x1] vectors of length x2.
//   Demonstrates: while loop, mul, data processing, load/store with offsets.
// ─────────────────────────────────────────────────────────────────────────────
    .global _vector_dot
    .type _vector_dot, @function

_vector_dot:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x3, #0              // accumulator = 0
    mov x4, #0              // index = 0

_vector_dot_loop:
    cmp x4, x2
    b.ge _vector_dot_done   // while index < length

    ldr x5, [x0, x4, lsl #3]  // a[i]
    ldr x6, [x1, x4, lsl #3]  // b[i]
    mul x7, x5, x6            // a[i] * b[i]
    add x3, x3, x7            // acc += product

    add x4, x4, #1            // i++
    b _vector_dot_loop

_vector_dot_done:
    mov x0, x3
    ldp x29, x30, [sp], #16
    ret


// ─────────────────────────────────────────────────────────────────────────────
// Data section — constants used by the above functions
// ─────────────────────────────────────────────────────────────────────────────

    .section __DATA, __data
    .align 3

_test_array:
    .quad 10
    .quad 25
    .quad 7
    .quad 42
    .quad 13
    .quad 88
    .quad 3
    .quad 61

_test_array_len:
    .quad 8
