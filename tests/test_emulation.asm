#cdecls C,LIST,"msp430FR5739.h"

        .text
        .global reset

reset:

test_emulation:
        mov     #0x1234, r5
        and     #0x00ff, r5

        .section    ".reset_vector"
        .word       reset

        .end

