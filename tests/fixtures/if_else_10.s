    .text
    .global _demo_if_else

_demo_if_else:
    stp x29, x30, [sp, #-48]!
    mov x29, sp

    // 1. Simple if (positive check)
    cmp x0, #0
    b.le _skip1
    add x0, x0, #1
_skip1:

    // 2. If/else
    cmp x1, #10
    b.lt _else2
    mov x1, #0
    b _end2
_else2:
    add x1, x1, #1
_end2:

    // 3. If with cbz (check null)
    cbz x2, _skip3
    ldr x3, [x2, #8]
_skip3:

    // 4. If with cbnz (check nonzero)
    cbnz x4, _body4
    mov x4, #1
_body4:

    // 5. If with tbz (test bit 0 — even check)
    tbnz x5, #0, _skip5
    add x5, x5, #1
_skip5:

    // 6. If with tbnz (test bit — sign check)
    tbz x6, #63, _skip6
    neg x6, x6
_skip6:

    // 7. Nested if/else
    cmp x7, #0
    b.le _outer_else7
    cmp x7, #100
    b.gt _inner_else7
    add x7, x7, #10
    b _outer_end7
_inner_else7:
    sub x7, x7, #10
    b _outer_end7
_outer_else7:
    mov x7, #50
_outer_end7:

    // 8. Multiple sequential if/else
    cmp x8, #5
    b.ne _else8a
    mov x8, #50
    b _end8a
_else8a:
    cmp x8, #10
    b.ne _else8b
    mov x8, #100
    b _end8b
_else8b:
    mov x8, #0
_end8b:
_end8a:

    // 9. If with cmp + b.ge (range guard)
    cmp x9, #0
    b.lt _skip9
    cmp x9, #255
    b.gt _skip9
    and x9, x9, #0xFF
_skip9:

    // 10. If/else with fcmp (float check)
    fcmp d0, d1
    b.ge _else10
    fadd d0, d0, d1
    b _end10
_else10:
    fsub d0, d0, d1
_end10:

    ldp x29, x30, [sp], #48
    ret
