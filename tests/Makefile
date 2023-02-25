AS = msp430-as
LD = msp430-ld


all: test.hex test_modes.hex test_disasm.hex test_emulation.hex

test.hex: test2.asm
	$(AS) -o test.obj test2.asm -al=test.lst
	$(LD) -T test.cmd -o test.out test.obj
	objcopy -O ihex test.out test.hex

test_modes.hex: test_modes.asm
	$(AS) -o test_modes.obj test_modes.asm -al=test_modes.lst
	$(LF) -T test.cmd -o test_modes.out test_modes.obj
	objcopy -O ihex test_modes.out test_modes.hex

test_disasm.hex: test_disasm.asm
	$(AS) -o test_disasm.obj test_disasm.asm -al=test_disasm.lst
	$(LD) -T test.cmd -o test_disasm.out test_disasm.obj
	objcopy -O ihex test_disasm.out test_disasm.hex

test_emulation.hex: test_emulation.asm
	$(AS) -o test_emulation.obj test_emulation.asm -al=test_emulation.lst
	$(LD) -T test.cmd -o test_emulation.out test_emulation.obj
	objcopy -O ihex test_emulation.out test_emulation.hex
