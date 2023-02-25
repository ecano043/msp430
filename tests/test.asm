#cdecls C,LIST,"msp430FR5739.h"

        .text
        .global reset

reset:

test_modes:
        nop
        reti

        rrc r7
        rrc 123(r5)
        rrc @r5
        rrc @r5+
        rrc &1234
        rrc.b r3
        rrc.b 123(r6)
        rrc.b &1234
        rrc.b 1234

        jmp 234
        jnc 234

        mov r4, r11
        mov 321(r7), r12
        mov 321(r7), &322
        mov @r5, r12
        mov @r5, &322
        mov @r5+, r12
        mov @r5+, &322

        reti
        rrc r4
        RRC R4
        rrc r15
        mov r1, r5
        rra 123(r5)
        nop
        swpb @R7
        swpb @r8+
        sxt @r4
        mov #123, r4
        jmp 422

        .section    ".reset_vector"
        .word       reset

        .end
