#cdecls C,LIST,"msp430FR5739.h"

        .text
        .global reset

reset:

test_modes:
;       rrc     r0      ; ERROR: No se puede rotar el PC - error de compilacion
        rrc     r1
        rrc     r2
        rrc     r3
        rrc     r4

;       rrc.b   r0      ; ERROR: No se puede rotar el PC - error de compilacion
        rrc.b   r1
        rrc.b   r2
        rrc.b   r3
        rrc.b   r4

;       rra     r0      ; ERROR: No se puede rotar el PC - error de compilacion
        rra     r1
        rra     r2
        rra     r3
        rra     r4

;       rra.b   r0      ; ERROR: No se puede rotar el PC - error de compilacion
        rra.b   r1
        rra.b   r2
        rra.b   r3
        rra.b   r4

        push    r0
        push    r1
        push    r2
        push    r3
        push    r4

        push.b  r0
        push.b  r1
        push.b  r2
        push.b  r3
        push.b  r4

;       rrc     0(r0)   ; Error: rrc: attempt to rotate the PC register
        rrc     2(r0)   ; Funciona!
        rrc.b   2(r0)
;       rrc     6(r2)   ; Error: r2 should not be used in indexed addressing mode
        rrc     18(r3)
;       rrc     @r0     ; Error: cannot use indirect addressing with the PC
        rrc     @r1
        rrc.b   @r2
        rrc     @r3
        rrc.b   @r4
        rrc     @r1+
        rrc     @r2+
        rrc     @r3+
        rrc     @r4+

        push    5(r1)
;       push    5(r2)   ; Error: r2 should not be used in indexed addressing mode
        push    5(r3)
        push    @r2
        push    @r2+
        push    @r3
        push    @r3+

        swpb    r0
        swpb    r2
        swpb    r3
        swpb    r1
        swpb.b  r5

;       swpb    5(r0)   ; Error: cannot use indirect addressing with the PC
;       swpb    @r0     ; Error: cannot use indirect addressing with the PC

        sxt     r0
        sxt     r1
        sxt     r2
        sxt     r3
        sxt     r4

        sxt.b   r4
        sxt     12(r3)
        sxt     @r3
        sxt     @r4
        sxt.b   @r4

        call.b  2      ; Compiler error?
        call    1234
        call    #1234
        call    r5
        call.b  r5
        call    @r6
        call    &1234

        reti
        reti.b

        mov     r0, r4
        mov     r1, r4
        mov     r2, r4
        mov     r3, r4
        mov     r4, r4
        mov     #0, r4

        mov     #0, 123(R5)
        mov     #321, 123(R5)
        mov.b   #0, 123(R5)
        mov.b   #321, 123(R5)   ; 321 > 1 byte
        mov     #0, 123(R0)
        mov     #321, 123(R0)

        add     #0, 123(R5)
        add     #321, 123(R5)
        add.b   #0, 123(R5)
        add.b   #321, 123(R5)   ; 321 > 1 byte
        add     #0, 123(R0)
        add     #321, 123(R0)

        addc    #0, 123(R5)
        addc    #321, 123(R5)
        addc.b  #0, 123(R5)
        addc.b  #321, 123(R5)   ; 321 > 1 byte
        addc    #0, 123(R0)
        addc    #321, 123(R0)

        sub     #0, 123(R5)
        sub     #321, 123(R5)
        sub.b   #0, 123(R5)
        sub.b   #321, 123(R5)   ; 321 > 1 byte
        sub     #0, 123(R0)
        sub     #321, 123(R0)

        subc    #0, 123(R5)
        subc    #321, 123(R5)
        subc.b  #0, 123(R5)
        subc.b  #321, 123(R5)   ; 321 > 1 byte
        subc    #0, 123(R0)
        subc    #321, 123(R0)

        cmp     #0, 123(R5)
        cmp     #321, 123(R5)
        cmp.b   #0, 123(R5)
        cmp.b   #321, 123(R5)   ; 321 > 1 byte
        cmp     #0, 123(R0)
        cmp     #321, 123(R0)

        dadd    #0, 123(R5)
        dadd    #321, 123(R5)
        dadd.b  #0, 123(R5)
        dadd.b  #321, 123(R5)   ; 321 > 1 byte
        dadd    #0, 123(R0)
        dadd    #321, 123(R0)

        bit     #0, 123(R5)
        bit     #321, 123(R5)
        bit.b   #0, 123(R5)
        bit.b   #321, 123(R5)   ; 321 > 1 byte
        bit     #0, 123(R0)
        bit     #321, 123(R0)

        bic     #0, 123(R5)
        bic     #321, 123(R5)
        bic.b   #0, 123(R5)
        bic.b   #321, 123(R5)   ; 321 > 1 byte
        bic     #0, 123(R0)
        bic     #321, 123(R0)

        bis     #0, 123(R5)
        bis     #321, 123(R5)
        bis.b   #0, 123(R5)
        bis.b   #321, 123(R5)   ; 321 > 1 byte
        bis     #0, 123(R0)
        bis     #321, 123(R0)

        xor     #0, 123(R5)
        xor     #321, 123(R5)
        xor.b   #0, 123(R5)
        xor.b   #321, 123(R5)   ; 321 > 1 byte
        xor     #0, 123(R0)
        xor     #321, 123(R0)

        and     #0, 123(R5)
        and     #321, 123(R5)
        and.b   #0, 123(R5)
        and.b   #321, 123(R5)   ; 321 > 1 byte
        and     #0, 123(R0)
        and     #321, 123(R0)


        .section    ".reset_vector"
        .word       reset

        .end
