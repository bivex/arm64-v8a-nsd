    .text
    .global _score
    .type _score, @function

_score:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    mov x0, #0

    // if x1 > 0
    cmp x1, #0
    b.le _score_else

    add x0, x0, x1
    b _score_endif

_score_else:
    mov x0, #0

_score_endif:
    // while x2 < 10
    mov x3, #0

_score_while:
    cmp x3, #10
    b.ge _score_while_end
    add x3, x3, #1
    b _score_while

_score_while_end:
    // repeat...until style
_score_repeat:
    sub x0, x0, #1
    cmp x0, #50
    b.gt _score_repeat

    // switch on x4
    cmp x4, #0
    b.eq _score_case_zero
    cmp x4, #1
    b.eq _score_case_one
    b _score_switch_end

_score_case_zero:
    mov x0, #0
    b _score_switch_end

_score_case_one:
    mov x0, #1

_score_switch_end:
    ldp x29, x30, [sp], #16
    ret

    .global _normalize
    .type _normalize, @function

_normalize:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    cmp x0, #0
    b.ge _normalize_else
    mov x0, #0
    b _normalize_endif

_normalize_else:
    // x0 is already >= 0, keep it

_normalize_endif:
    ldp x29, x30, [sp], #16
    ret
