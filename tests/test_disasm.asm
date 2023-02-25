#cdecls C,LIST,"msp430FR5739.h"

        .text
        .global reset

reset:

test_modes:
        swpb    r4
        swpb    123(r4)
        swpb    @r4
        swpb    @r4+
        sxt     r4
        sxt     123(r4)
        sxt     @r4
        sxt     @r4+
        call    r4
        call    123(r4)
        call    @r4
        call    @r4+
        reti
        rrc     r8
        rrc.b   123(r8)
        rrc     r8
        rrc     r8
        rra     r8
        rra     r8
        rra.b   r8
        push    r8
        push.b  r8

        jnz     256
        jz      -256
        jnc     256
        jc      32
        jn      -32
        jge     2
        jl      -2
        jmp     0

        MOV     R5, R6

        .section    ".reset_vector"
        .word       reset

        .end
