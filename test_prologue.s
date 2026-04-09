.section __TEXT,__text,regular,pure_instructions
.build_version macos, 13, 0 sdk_version 13, 0
.globl _main
.p2align 2

_main:
    mov X2, #100
    mov X3, #4
    stp X0, X1, [SP, #-16]!
    stp X2, X3, [SP, #-16]!
    stp X4, X5, [SP, #-16]!
    stp X6, X7, [SP, #-16]!
    stp X8, X9, [SP, #-16]!
    stp X10, X11, [SP, #-16]!
    stp X12, X13, [SP, #-16]!
    stp X14, X15, [SP, #-16]!
    stp X16, X17, [SP, #-16]!
    stp X18, LR, [SP, #-16]!
    mov X1, #2
    mov X2, X2
    str X1, [SP, #-32]!
    str X2, [SP, #8]
    ret
