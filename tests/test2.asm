#cdecls C,LIST,"msp430FR5739.h"

        .text
        .global reset

reset:

test_modes:
        mov     #-7, R7
        mov	#-13, R5	
        cmp	R4, R5
        and	R4, R6
        bit	R7, R8
        jc	mon
        subc	R10, R5
        and	R7, R6
mon:
	mov	#0x9, R10
	ret

        .section    ".reset_vector"
        .word       reset

        .end

