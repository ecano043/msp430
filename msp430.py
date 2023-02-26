#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  legv8.py
#
#  Copyright 2020 John Coppens <john@jcoppens.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#


from memory import Memory
import pdb, os
import pyparsing as pp

DEBUG = False

#Archivos de test
TEST_FILE = "tests/test.hex"
TEST_MODES_FILE = "tests/test_modes.hex"
TEST_DISASM_FILE = "tests/test_disasm.hex"
TEST_EMULATION_FILE = "tests/test_emulation.hex"

PATH_PPAL = os.path.dirname(os.path.abspath(__file__)) + "/" # Ruta absoluta del archivo

def decode_signed(value, length):
    mask = 1 << (length-1)
    if value & mask == 0:  # Positivo
        return value & (mask - 1)
    else:                               # Negativo
        return -((~value & (mask - 1)) + 1)


class Registers():
    """ Vectores en tablas
        memory      0xfffe  Vector de reset (= PC inicial)
                    0xfc00  Inicio de programa

        ram         0x1c00-0x1fff
                    0x2000  SP (se inicialice automaticamente por el chip)

        fram        Depende del modelo de chip
    """
    PC  = 0
    SP  = 1
    SR  = 2 # Estado de registro (flag)
    CG1 = 2
    CG2 = 3

    # Nombres de las banderas para uso en 'dump' y para uso 'gui' --> tuplas
    FL_BITS = ("C", "Z", "N", "GIE", "NCPU", "NOSC", "SCG0", "SCG1", "V")

    NAMES = ("R0/PC", "R1/SP", "R2/SR/CG1", "R3/CG2",
             "R4", "R5", "R6", "R7",
             "R8", "R9", "R10", "R11",
             "R12", "R13", "R14", "R15")
    def __init__(self, pc, sp):
        self.reg = [0] * 16 # Lista de 16 elementos inicializados en 0, para representar los 16 registros.
        self.reg[self.PC] = pc # el PC es el R0, entonce,s en la lista reg: reg[0]
        self.reg[self.SP] = sp # reg[1]


    def set_reg(self, reg, value):
        self.reg[reg] = value


    def get_reg(self, reg):
        return self.reg[reg]


    def set_flag(self, flag, newval):
        if newval:
            self.reg[self.SR] |= (1 << flag) # SR = SR + (1 << flag). Flag puede valer 0 o 1. Si es 1, pongo en 1 el bit correspondiente a <flag> en la lista de 8 bits
        else:
            self.reg[self.SR] &= ~(1 << flag) # Si no se especifica un nuevo valor, se pone el flag en 1, y los demás flags en 0


    def set_flag_by_name(self, flag, newval):
        bit = self.FL_BITS.index(flag) # índice de esa flag dentro de la tupla de flags
        self.set_flag(bit, newval)


    def get_flag(self, flag):
        """ Return True if Flags[flag] es 1
        """
        return (self.reg[self.SR] & (1 << flag)) != 0 # AND entre el valor del flag con un 1


    def get_flag_by_name(self, flag):
        """ Return True if Flags[flag] es 1
        """
        bit = self.FL_BITS.index(flag)
        return self.get_flag(bit)


    def dump(self):
        for quad in range(0, 16, 4):
            t = ""; d = ""
            t += "  ".join(
                ["{:12s}".format(self.NAMES[quad+i]) for i in range(4)])
            d += "  ".join(
                ["0x{0:04x}/{0:<5d}".format(self.reg[quad + i]) for i in range(4)]) # Formato hex y decimal
            print(t + "\n  " + d)

        tflags = self.reg[self.SR]

        s = ""
        print("\nStatus:")
        for lbl in self.FL_BITS:
            s += "  {}: {}".format(lbl, tflags & 1)
            tflags >>= 1 # Se desplaza el bit leído a la derecha, para leer el próximo bit de flag
        print(s)


class MSP430():
    M4      = 0xf000
    M6      = 0xfc00
    M9      = 0xff80

    # Instrucción    Tipo    OPCODE   B/W      Modo de operando
    OPCODES = (
        # Operaciones con un solo operando - hay tres 'subtipos'
        #   Instrucciones que pueden especificarse con .B o .W
        ("rrc",     M9, 0x1000, "SINGLE_BW", "SINGLE"),
        ("rra",     M9, 0x1100, "SINGLE_BW", "SINGLE"),
        ("push",    M9, 0x1200, "SINGLE_BW", "SINGLE"),
        #   Instrucciones que no pueden llevar .B (Byte) o .W (siempre Word)
        ("swpb",    M9, 0x1080, "SINGLE", "SINGLE"),
        ("sxt",     M9, 0x1180, "SINGLE", "SINGLE"),
        ("call",    M9, 0x1280, "SINGLE", "SINGLE"),
        #   Instrucción que no necesita operando
        ("reti",    M9, 0x1300, "SINGLE_RETI", "NOOPD"),

        # Instrucciones de tipo salto
        ("jnz",     M6, 0x2000, 'JMP', "JUMP"),
        ("jz",      M6, 0x2400, 'JMP', "JUMP"),
        ("jnc",     M6, 0x2800, 'JMP', "JUMP"),
        ("jc",      M6, 0x2C00, 'JMP', "JUMP"),
        ("jn",      M6, 0x3000, 'JMP', "JUMP"),
        ("jge",     M6, 0x3400, 'JMP', "JUMP"),
        ("jl",      M6, 0x3800, 'JMP', "JUMP"),
        ("jmp",     M6, 0x3C00, 'JMP', "JUMP"),

        # Instrucciones con dos operandos
        #   Estas instrucciones siempre llevan dos operandos - sin excepciones
        ("mov",     M4, 0x4000, "DOUBLE", "DOUBLE"),
        ("add",     M4, 0x5000, "DOUBLE", "DOUBLE"),
        ("addc",    M4, 0x6000, "DOUBLE", "DOUBLE"),
        ("subc",    M4, 0x7000, "DOUBLE", "DOUBLE"),
        ("sub",     M4, 0x8000, "DOUBLE", "DOUBLE"),
        ("cmp",     M4, 0x9000, "DOUBLE", "DOUBLE"),
        ("dadd",    M4, 0xa000, "DOUBLE", "DOUBLE"),
        ("bit",     M4, 0xb000, "DOUBLE", "DOUBLE"),
        ("bic",     M4, 0xc000, "DOUBLE", "DOUBLE"),
        ("bis",     M4, 0xd000, "DOUBLE", "DOUBLE"),
        ("xor",     M4, 0xe000, "DOUBLE", "DOUBLE"),
        ("and",     M4, 0xf000, "DOUBLE", "DOUBLE")
    )

    EMULATED_OPCODES = (
        ("adc",     0,  0x5300, "SINGLE_BW", "SINGLE"),
        ("br",      0,  0x4000, "JMP_REL", "SINGLE"),
        ("clr",     0,  0x4300, "SINGLE_BW", "SINGLE"),
        ("clrc",    0,  0xc302, "SINGLE_NOP", "NOOPD" ),
        ("clrn",    0,  0xc222, "SINGLE_NOP", "NOOPD"),
        ("clrz",    0,  0xc322, "SINGLE_NOP", "NOOPD"),
        ("dadc",    0,  0xa300, "SINGLE_BW", "SINGLE"),
        ("dec",     0,  0x8310, "SINGLE_BW", "SINGLE"),
        ("decd",    0,  0x8320, "SINGLE_BW", "SINGLE"),
        ("dint",    0,  0xc232, "SINGLE_NOP", "NOOPD"),
        ("eint",    0,  0xd232, "SINGLE_NOP", "NOOPD"),
        ("inc",     0,  0x5310, "SINGLE_BW", "SINGLE"),
        ("incd",    0,  0x5320, "SINGLE_BW", "SINGLE"),
        ("inv",     0,  0xe330, "SINGLE_BW", "SINGLE"),
        ("nop",     0,  0x4303, "SINGLE_NOP", "NOOPD"),
        ("pop",     0,  0x4130, "SINGLE",        "SINGLE"),
        ("ret",     0,  0x4130, "SINGLE_NOP",    "NOOPD"),
        ("rla",     0,  0x5000, "SINGLE_RPT_BW", "SINGLE"),
        ("rlc",     0,  0x6000, "SINGLE_RPT_BW", "SINGLE"),
        ("sbc",     0,  0x7300, "SINGLE_BW", "SINGLE"),
        ("setc",    0,  0xd302, "SINGLE_NOP", "NOOPD"),
        ("setn",    0,  0xd222, "SINGLE_NOP", "NOOPD"),
        ("setz",    0,  0xd322, "SINGLE_NOP", "NOOPD"),
        ("tst",     0,  0x9300, "SINGLE_BW", "SINGLE")
    )

    def __init__(self, memory):
        self.memory = memory
        ram = self.memory.areas["RAM"]
        self.registers = Registers(pc = self.memory.read_word(0xfffe),
                                   sp = ram.base + ram.size)


    def find_opcode(self, opcode):
        """ Retorna mnem, mask, valu, form, kind después de veirificar que el opcode corresponde
            a una instrucción
        """
        for mnem, mask, value, form, kind in self.OPCODES:
            if (opcode & mask) == value:
                return mnem, mask, value, form, kind
        return None


    def single_sd(self, opcode):
        """ Instrucción de operando único:
            Retornar modo de direccionamimiento, número de registro
        """
        return (opcode >> 4) & 3, opcode & 0x000f # 3 = 11 --> shift para que queden los últimos 2 bits que indican modo de direcc. Con & 11 obtengo el modo
        # opcode & 0x0001111 me da los últimos 4 bits del opc, que es el n° de registro


    def double_src(self, opcode):
        """ Instrucción de operando doble:
            Retornar modo de direccionamiento, número de registro fuente,
        """
        return (opcode >> 4) & 3, (opcode >> 8) & 0x000f


    def double_dst(self, opcode):
        """ Instrucción de operando doble:
            Retornar modo de direccionamimiento, número de registro destino,
        """
        return (opcode >> 7) & 1, opcode & 0x000f


    def byte_op(self, opcode):
        """ Retorna true si opera con byte.
            False si opera con una palabra (16 bits)
        """
        #0 = 16-bit     1 = 8-bit
        return (opcode & 0x40) != 0 #0x40 = 01000000



"""
     ____  _                                  _     _
    |  _ \(_)___  __ _ ___ ___  ___ _ __ ___ | |__ | | ___ _ __
    | | | | / __|/ _` / __/ __|/ _ \ '_ ` _ \| '_ \| |/ _ \ '__|
    | |_| | \__ \ (_| \__ \__ \  __/ | | | | | |_) | |  __/ |
    |____/|_|___/\__,_|___/___/\___|_| |_| |_|_.__/|_|\___|_|

"""

class MSP430_disassembler(MSP430): # Hereda de la clase MSP430
    def __init__(self, memory):
        super(MSP430_disassembler, self).__init__(memory)


    def single_operand(self, opcode, pc):
        """
        Devuelve el operando y el pc
        """
        mode, reg = self.single_sd(opcode)

        if mode == 0:
            line = "R{}".format(reg)
        elif mode == 1: # El operando está en la memoria
            opd = self.memory.read_word(pc)
            if reg == 2:
                line = "&{}".format(opd) # El operando está en la memoria en el registro reg
            else:
                line = "{}(R{})".format(opd, reg) # El operando está fuera del paréntesis, y el resultado va al reg. Ej: rrc 2(R4)
            pc += 2

        elif mode == 2:
            line = "@R{}".format(reg) # El operando está en la memoria, en la dirección de reg

        elif mode == 3:
            if reg == 0:
                opd = self.memory.read_word(pc)
                line = "#{}".format(opd)
                pc += 2
            else:
                line = "@R{}+".format(reg) # Es un Rn ++

        return pc, line


    def double_operand(self, opcode, pc):
        """
        Devuelve los 2 operandos, y el pc
        """

        dmode, dreg = self.double_dst(opcode) # Modo de direccionamiento, registro destino
        smode, sreg = self.double_src(opcode) # Modo de direccionamiento, registro origen
        line = ""

        if smode == 0:
            if   sreg == Registers.PC:  line = "R0"
            elif sreg == Registers.SP:  line = "SP"
            elif sreg == Registers.SR:  line = "SR"
            elif sreg == Registers.CG2: line = "#0" # Modo de direccionamiento especial. R3, modo 0 = constante 0
            else:                       line = "R{}".format(sreg)

        elif smode == 1:
            if sreg == Registers.PC:
                opd = self.memory.read_word(pc)
                pc += 2
                line = "{}".format(opd)

            if sreg == Registers.CG1:
                opd = self.memory.read_word(pc)
                pc += 2
                line = "&{}".format(opd)

        elif smode == 2:
            if sreg == Registers.CG1:
                line = "#4"
            elif sreg == Registers.CG2:
                line = "#2"

        elif smode == 3:
            if sreg == Registers.PC:
                opd = self.memory.read_word(pc)
                pc += 2
                line = "#{}".format(opd)

            elif sreg == Registers.CG1:
                line = "#8"

            elif sreg == Registers.CG2:
                line = "#{}".format(sreg)

        line += ", "

        if dmode == 0:
            line += "R{}".format(dreg)

        elif dmode == 1:
            opd = self.memory.read_word(pc)
            pc += 2
            line += "{}(R{})".format(opd, dreg)

        return pc, line


    def disassemble_one(self, pc):
        """
        Lee una palabra de la memoria y desensambla la instrucción
        """
        opcode = self.memory.read_word(pc)
        byte_op = self.byte_op(opcode)
        pc += 2

        found = self.find_opcode(opcode)
        if found is None:
            return None

        mnem, mask, value, form, kind = found
        # Instrucciones de salto. Operando es dirección relativa.
        if form == "JMP":
            line = "{:8s}{}".format(mnem,
                    decode_signed(opcode & 0x03ff, 10) * 2) # uso esta máscara para obtener sólo los valores del desplazamiento (10 bits). El *2 es porque PC = PC + 2×offset

        # Instrucciones de simple operando
        elif form == "SINGLE_RETI":
            line =  "{:8s}".format(mnem)

        elif form == "SINGLE":
            pc, rest = self.single_operand(opcode, pc)
            line = "{:8s}{}".format(mnem, rest)

        elif form == "SINGLE_BW":
            pc, rest = self.single_operand(opcode, pc)
            line = "{:8s}{}".format(mnem + (".B" if byte_op else ""), rest)

        # Instrucciones de doble operando
        elif form == "DOUBLE":
            pc, rest = self.double_operand(opcode, pc)
            line = "{:8s}{}".format(mnem + (".B" if byte_op else ""), rest)

        # Instrucciones invalidas
        else:
            line = "Operando no decodificado"

        return pc, line

"""
     _____                 _       _
    | ____|_ __ ___  _   _| | __ _| |_ ___  _ __
    |  _| | '_ ` _ \| | | | |/ _` | __/ _ \| '__|
    | |___| | | | | | |_| | | (_| | || (_) | |
    |_____|_| |_| |_|\__,_|_|\__,_|\__\___/|_|

"""

class MSP430_emulator(MSP430):
    def __init__(self, memory):
        super(MSP430_emulator, self).__init__(memory)


    def get_src(self, pc, mode, reg):
        """
        Devuelve el operando origen (según el modo de direccionamiento del mismo)
        """
        if mode == 0:
            return pc, self.registers.get_reg(reg) # operando es el registro

        elif mode == 1:
            if reg == Registers.PC:
                opd = self.memory.read_word(pc, check_initialized = False)
                pc += 2
                return pc, self.memory.read_word(pc + opd) # El operando está en la memoria, dirección PC + opd

            elif reg == Registers.CG1:
                opd = self.memory.read_word(pc, check_initialized = False)
                pc += 2
                return pc, self.memory.read_word(opd) # el operando está en la memoria, dirección opd

        elif mode == 2:
            if reg == Registers.CG1:
                return pc, 4 # el operando es la constante 4

        else: # Modo 3
            if reg == Registers.PC:                 # Immediate
                opd = self.memory.read_word(pc, check_initialized = False)
                pc += 2
                return pc, opd # El operando es la siguiente palabra

            elif reg == Registers.CG1:
                return pc, 8 # el operando es la constante 8

            elif reg == Registers.CG2:
                return pc, -1 # el operando es la constante -1


    def set_dst(self, pc, mode, reg, newval):
        """
        Setea el registro destino (dependiendo del modo de direccionamiento)
        """
        if mode == 0:
            self.registers.set_reg(reg, newval)
            return pc

        elif mode == 1:
            if reg == Registers.PC:
                opd = self.memory.read_word(pc, check_initialized = False)
                pc += 2
                return pc, self.memory.read_word(pc + opd)

            elif reg == Registers.CG1:
                opd = self.memory.read_word(pc, check_initialized = False)
                pc += 2
                return pc, self.memory.read_word(opd)

        elif mode == 2:
            pass

        else:
            pass


    """
     ____  _             _         ___            _
    / ___|(_)_ __   __ _| | ___   / _ \ _ __   __| |
    \___ \| | '_ \ / _` | |/ _ \ | | | | '_ \ / _` |
     ___) | | | | | (_| | |  __/ | |_| | |_) | (_| |
    |____/|_|_| |_|\__, |_|\___|  \___/| .__/ \__,_|
                   |___/               |_|
    """
    def op_rrc(self, in_val, byte_op):
        """
        Rotación a la derecha (1 bit) con carry
        """
        # RRC.B:   C -> b7 -> b6 -> .... -> b1 -> b0 -> C
        # RRC[.W]: C -> b15 -> b14 -> .... -> b1 -> b0 -> C
        regs = self.registers
        msb = 0x80 if byte_op else 0x8000
        new_C = (in_val & 1) != 0 # Si el último bit de in_val es 1, tengo Carry
        in_val >>= 1
        if regs.get_flag_by_name("C"):
            in_val |= msb # Ingresa el carry, si hbaía uno antes, por izquierda

        regs.set_flag_by_name("C", new_C)
        regs.set_flag_by_name("V", False)
        regs.set_flag_by_name("Z", in_val == 0)
        regs.set_flag_by_name("N", (in_val & msb) != 0)
        return in_val


    def op_rra(self, in_val, byte_op):
        """
        Rotación a la derecha (aritmética)
        """
        # RRA.B:   b15 -> b7 -> b6 -> .... -> b1 -> b0 -> C
        # RRA[.W]: b15 -> b15 -> b14 -> .... -> b1 -> b0 -> C
        regs = self.registers
        msb = 0x80 if byte_op else 0x8000
        new_C = (in_val & 1) != 0 # carry o no?
        if (in_val & msb) != 0:             # Valor es negativo?
            in_val = (in_val >> 1) | msb    # OR con msb para volver a poner el primer bit en 1 (negativo)
        else:
            in_val >>= 1                    # sino sigue positivo

        # Setear las banderas segun especificaciones (C ya está seteado)
        regs.set_flag_by_name("C", new_C)
        regs.set_flag_by_name("V", False)
        regs.set_flag_by_name("Z", in_val == 0)
        regs.set_flag_by_name("N", (in_val & msb) != 0)
        return in_val


    def op_push(self, in_val, byte_op):
        """
        Insertar en la pila
        """
        # SP-2 -> SP
        # in_val -> [SP]
        regs = self.registers
        new_SP = regs.get_reg(regs.SP) - 2 # Para insertar nueva dirección en el SP, le resto a SP 2, donde iría el nuevo valor
        self.memory.ram.write_word(new_SP, in_val) # Se inserta en la memoria
        self.registers.set_reg(regs.SP, new_SP) # Se actualiza el registro SP


    def op_call(self): # Llama a una subrutina
        # SP-2 -> SP
        # in_val -> [SP]
        regs = self.registers
        new_SP = regs.get_reg(regs.SP) - 2
        self.memory.ram.write_word(new_SP, regs.get_reg(regs.PC)) # Inserta en el SP la dirección del PC (dónde volver después de subrutina)
        self.registers.set_reg(regs.SP, new_SP)


    def op_swpb(self, in_val):                  # SWPB --> Swap bytes
        high = (in_val << 8) & 0xff00
        low = in_val >> 8
        return (high + low)

    def op_sxt(self, in_val): # Toma el primer bit del y lo extiende a la izquierda
        """
        Extiende byte a word
        """
        mask =0x0080
        #       0000 0000 1000 0000     0x0080
        #       1111 1111 0001 0001     0xff11 (in_val)
        #--------------------------

        #resultado-> 0000 0000 0001 0001

        dst = (in_val & 0x00ff) if ((in_val & mask) == 0) else (in_val | 0xff00)

        # Status register update
        regs = self.registers                               #accedemos a los registros

        regs.set_flag_by_name("C", dst != 0)
        regs.set_flag_by_name("V", False)
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("N", (dst & mask) != 0)           #me fijo si el ultimo bit mas significativo es 1 o 0
        #print("aca lo reslvio ",dst)
        return dst


    """
     ____              _     _         ___            _
    |  _ \  ___  _   _| |__ | | ___   / _ \ _ __   __| |
    | | | |/ _ \| | | | '_ \| |/ _ \ | | | | '_ \ / _` |
    | |_| | (_) | |_| | |_) | |  __/ | |_| | |_) | (_| |
    |____/ \___/ \__,_|_.__/|_|\___|  \___/| .__/ \__,_|
                                           |_|
    """
    def op_mov(self, src, dst, byte_op):
        """ Operacioon MOV: Simplemente toma el dato fuente, y
            lo retorna com resultado.
            El Status Register no se modifica.
        """
        return src & (0x00ff if byte_op else 0xffff)


    def op_and(self, src, dst, byte_op):
        """ Operacioon AND: Realizar la función AND entre src, y dst.
            El Status Register se modifica.
        """
        dst = (dst & src) & (0x00ff if byte_op else 0xffff)

        # Status register update
        regs = self.registers
        mask = 0x0080 if byte_op else 0x8000 # Toma el primer bit para ver si es neg o pos
        regs.set_flag_by_name("C", dst != 0)
        regs.set_flag_by_name("V", False)
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("N", (dst & mask) != 0)
        return dst

    def op_cmp(self, src, dst, byte_op):                # CMP --> Compare source word or byte and destination word or byte
        """ Operacion CMP: Compara los bits entre src y dst.
            El Status Register se modifica.
        """
        ret = dst
        aux = dst & (0x00ff if byte_op else 0xffff)
        dst = (dst - src) & (0x00ff if byte_op else 0xffff)

        # Status register update
        regs = self.registers
        mask = 0x0080 if byte_op else 0x8000
        regs.set_flag_by_name("C", (dst & mask) != 0)        # El carry siempre está cuando el primer bit está en 1
        regs.set_flag_by_name("V", ((decode_signed(aux, 16) < 0) & (decode_signed(src, 16) > 0) & (decode_signed(dst, 16) < 0))
                                 | ((decode_signed(aux, 16) > 0) & (decode_signed(src, 16) < 0) & (decode_signed(dst, 16) > 0)))   # -SUB+ --> - = V o +SUB- --> + = V
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("N", decode_signed(dst, 16) < 0)        # Explicacion ELI   
        return ret              # verificar V y C, ver porque no cambia el seteo por consola de flags

    def op_bit(self, src, dst, byte_op):                # BIT --> Bit Test
        """ Operacion BIT: AND entre bits de src y dst. No devuelve resutlado.
            El Status Register se modifica.
        """
        ret = dst
        dst = (src & dst) & (0x00ff if byte_op else 0xffff)
        
        regs = self.registers
        mask = 0x0080 if byte_op else 0x8000
        regs.set_flag_by_name("C", dst != 0)
        regs.set_flag_by_name("V", False)
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("N", (dst & mask) != 0)     
        return ret

    def op_subc(self, src, dst, byte_op):                # SUBC --> Subtraction Carry
        """ Operacion SUBC: Resta al destino la fuente con carry.
            El Status Register se modifica.
        """
        aux = dst
        regs = self.registers
        if (regs.get_flag_by_name("C")):
            c = 1
        else:
            c = 0
        dst = ((-decode_signed(src, 16)) + c + dst) & (0x00ff if byte_op else 0xffff)

        mask = 0x0080 if byte_op else 0x8000
        regs.set_flag_by_name("C", (dst & mask) != 0)
        regs.set_flag_by_name("V", ((decode_signed(src, 16) < 0) & (decode_signed(aux, 16) > 0) & (decode_signed(dst, 16) < 0))
                                 | ((decode_signed(src, 16) > 0) & (decode_signed(aux, 16) < 0) & (decode_signed(dst, 16) > 0)))
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("N", (dst & mask) != 0)  
        return dst

    def op_addc(self, src, dst, byte_op):                # ADDC --> Add Carry
        """ Operacion ADDC: Suma al destino la fuente con carry.
            El Status Register se modifica.
        """
        aux = dst
        regs = self.registers
        if (regs.get_flag_by_name("C")):
            c = 1
        else:
            c = 0
        dst = (src + dst + c) & (0x00ff if byte_op else 0xffff)

        mask = 0x0080 if byte_op else 0x8000
        regs.set_flag_by_name("C", (dst & mask) != 0)
        regs.set_flag_by_name("V", ((decode_signed(src, 16) < 0) & (decode_signed(aux, 16) < 0) & (decode_signed(dst, 16) > 0))
                                 | ((decode_signed(src, 16) > 0) & (decode_signed(aux, 16) > 0) & (decode_signed(dst, 16) < 0)))
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("N", (dst & mask) != 0)  
        return dst

    def op_xor(self, src, dst, byte_op):                # XOR --> Exclusive OR
        """ Operacion XOR: Realizar la función XOR entre src, y dst.
            El Status Register se modifica.
        """
        aux = dst
        dst = (dst ^ src) & (0x00ff if byte_op else 0xffff)

        # Status register update
        regs = self.registers
        mask = 0x0080 if byte_op else 0x8000
        regs.set_flag_by_name("C", dst != 0)
        regs.set_flag_by_name("V", (decode_signed(aux, 16) < 0) & (decode_signed(src, 16) < 0))
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("N", (dst & mask) != 0)       
        return dst

    def op_add(self, src, dst, byte_op):
        """ Operacion ADD: Toma el el segundo dato y se lo suma
            al primero como resultado.
            El Status Register se modifica.
        """
        mask = 0x0080 if byte_op else 0x8000

        dst = (dst + src) & mask

        flaga = True if (((dst & mask) == 0) & ((src & mask) == 0)) else False  # verdadero si ambos son positivos
        flagb = True if (((dst & mask) != 0) & ((src & mask) != 0)) else False  # verdadero si ambos son negativos

        # Status register update
        regs = self.registers

        regs.set_flag_by_name("N", (dst & mask) != 0)
        regs.set_flag_by_name("Z", dst == 0)
        regs.set_flag_by_name("C", (dst & mask) != 0)
        regs.set_flag_by_name("V", ( (((dst & mask)!=0) & flaga) | (((dst & mask)==0) & flagb) ) )
        return dst

    def op_bic(self, src, dst, byte_op):
        """ Operacion BIC: (clear bits in destination) Realizar and entre
            el inverso del operando 2 y el opernado destino.
            No se setean banderas
            
        """
        dst = (dst & ~src) & (0x00ff if byte_op else 0xffff)

        # Status register update
        # regs = self.registers
        # mask = 0x0080 if byte_op else 0x8000
        # regs.set_flag_by_name("C", dst != 0)
        # regs.set_flag_by_name("V", False)
        # regs.set_flag_by_name("Z", dst == 0)
        # regs.set_flag_by_name("N", (dst & mask) != 0)

        return dst

    def op_sub(self, src, dst, byte_op):
        """
        Se hace origen - destino
        """
        temp = True if (src>dst) else False 
        dst = (dst + ~(src) + 1) & (0x00ff if byte_op else 0xffff)
        # Status register update
        regs = self.registers                               #accedemos a los registros
        mask = 0x0080 if byte_op else 0x8000
        regs.set_flag_by_name("C", (dst & mask) == 1)
        regs.set_flag_by_name("V", (dst & mask) == 1)       #me fijo si el ultimo bit mas significativo es 1 o 0
        regs.set_flag_by_name("Z", dst == 0)#listo
        regs.set_flag_by_name("N", temp)    #listo      
        return dst
    
    def op_bis(self, src, dst, byte_op):
        """
        BIT set. Es un OR entre src y dst
        """
        dst = (dst | (src)) & (0x00ff if byte_op else 0xffff)
        #print("espues de hacer la operacion :", dst)
        return dst
    
    def op_dadd(self, src, dst, byte_op):
        """
        Suma decimal entre src y dts, con carry
        """
        ca = 0
        regs = self.registers               #accedemos a los registros
        if regs.get_flag_by_name("C"):      #aca coloco un 1 si el carry es 1 sino ya tiene el cero colocado
            ca = 1
        
        dst = (dst + src + ca ) & (0x00ff if byte_op else 0xffff)
        mask = 0x0080 if byte_op else 0x8000
        # Status register update
        regs.set_flag_by_name("C", (dst & mask) != 0)
        #regs.set_flag_by_name("V", False)
        regs.set_flag_by_name("Z", dst == 0 )
        regs.set_flag_by_name("N", (dst & mask) != 0)
        
        return dst


    def single_step(self):
        """
        Ejecuta una instrucción y aumenta el PC
        """
        regs = self.registers
        pc = regs.get_reg(0)
        opcode = self.memory.read_word(pc)
        pc += 2
        regs.set_reg(0, pc)

        found = self.find_opcode(opcode)
        if found is None:
            return None

        mnem, mask, value, form, kind = found
        byte_op = self.byte_op(opcode)
        # Instrucciones de salto. Operando es dirección relativa.
        if form == "JMP":
            jump = False
            if mnem == "JMP":
                jump = True
            elif mnem == "JNZ":
                jump = not regs.get_flag(regs.get_flag_by_name("Z")) # Si Z = 1, es negativo. JNZ indica que salta si != 0
            elif mnem == "JZ":
                jump = regs.get_flag(regs.get_flag_by_name("Z"))
            elif mnem == "JC":      
                jump = regs.get_flag(regs.get_flag_by_name("C"))
            elif mnem == "JNC":     
                jump = not regs.get_flag(regs.get_flag_by_name("C"))
            elif mnem == "JL":  # Jump si es menor
                jump = (regs.get_flag(regs.get_flag_by_name("N")) ^ regs.get_flag(regs.get_flag_by_name("V")))
            elif mnem == "JN": # Jump si es negativo
                jump = regs.get_flag(regs.get_flag_by_name("N"))
            elif mnem == "JGE": # Jump si es mayor o igual
                jump = not (regs.get_flag_by_name("N") ^ regs.get_flag_by_name("V"))

            if jump:
                offs = decode_signed(opcode & (mask ^ 0xffff), 10) # los 10 bits menos significativos indican el offset
                pc = pc + offs * 2
                regs.set_reg(0, pc + offs * 2)

        elif form == "DOUBLE":
            # pdb.set_trace()
            dmode, dreg = self.double_dst(opcode)
            smode, sreg = self.double_src(opcode)

            # Las funciones get_src y get_dst usan el pc porque hay modos de direcc que modifican el pc
            pc, src = self.get_src(pc, smode, sreg)
            _, dst = self.get_src(pc, dmode, dreg)   # ATTENTION

            # Diccionario para vincular operación con función que la ejecuta. Esta función se la paso como parámetro a la función set_dst, junto con los
            # parámetros que necesita cada función op (src, dst, byte_op)
            result = {"mov": self.op_mov,
                      "and": self.op_and,
                      "add": self.op_add,
                      "bic": self.op_bic,
                      "cmp": self.op_cmp,
                      "bit": self.op_bit,
                      "subc": self.op_subc,
                      "addc": self.op_addc,
                      "sub": self.op_sub,
                      "bis": self.op_bis,
                      "dadd": self.op_dadd,
                      "xor": self.op_xor}[mnem](src, dst, byte_op)

            pc = self.set_dst(pc, dmode, dreg, result)

        elif form == "SINGLE_BW":
            if mnem in ("RRC", "RRA", "PUSH"):
                mode, reg = self.single_sd(opcode)
                _, src = self.get_src(pc, mode, reg)

                result = {"RRC": self.op_rrc,
                          "RRA": self.op_rra,
                          "PUSH": self.op_push}[mnem](src, byte_op)

                pc = self.set_dst(pc, mode, reg, result)

        elif form == "SINGLE":
            if mnem in ("SXT", "SWPB", "CALL"):
                mode, reg = self.single_sd(opcode)
                _, src = self.get_src(pc, mode, reg)

                result = {"CALL": self.op_call,
                          "SWPB": self.op_swpb,
                          "SXT": self.op_sxt}[mnem](src)

                pc = self.set_dst(pc, mode, reg, result)

        elif form == "SINGLE_RETI":
            pass

        regs.set_reg(Registers.PC, pc)
        return


    """
        _                           _     _
       / \   ___ ___  ___ _ __ ___ | |__ | | ___ _ __
      / _ \ / __/ __|/ _ \ '_ ` _ \| '_ \| |/ _ \ '__|
     / ___ \\__ \__ \  __/ | | | | | |_) | |  __/ |
    /_/   \_\___/___/\___|_| |_| |_|_.__/|_|\___|_|

    """

class MSP430_assembler(MSP430):
    xref = {}

    def __init__(self, memory):
        super(MSP430_assembler, self).__init__(memory)

        # Convertir OPCODES en un diccionario, indexado por mnemonico
        self.mnemonics = {opc[0]: [opc[2], opc[4]] for opc in self.OPCODES}
        emul = {opc[0]: [opc[2], opc[4]] for opc in self.EMULATED_OPCODES}
        self.mnemonics.update( emul )

        # ~ print(self.mnemonics)

        # Crear una tabla de indice cruzado, indexado por tipo de operandos
        self.mnem_kinds = {}
        for key, val in self.mnemonics.items():
            if val[1] not in self.mnem_kinds:
                self.mnem_kinds[val[1]] = []
            self.mnem_kinds[val[1]].append(key)

        # ~ print(self.mnem_kinds)

        self.registers =       {"r{0:}".format(r): r for r in range(16)}
        self.registers.update( {"R{0:}".format(r): r for r in range(16)} )
        self.registers.update( {"pc": 0, "sp": 1, "sr": 2, "cg1": 2, "cg2": 3} )
        self.reg_names = " ".join(self.registers.keys())
        # ~ print(self.registers)

        self.parser = self.make_parser()


    def make_parser(self, which = "parser"):
        """ FLujo para decodificar, por ejemplo: mov @r5+, &322:

            code_line => opc_double (pp.oneOf(mnem_kinds["DOUBLE"]) + double_opds)
                opc_double => double_opds (two_bit_modes + pp.Suppress(",") + one_bit_modes)
                    double_opds => two_bit_modes (one_bit_modes | indirect_auto | indirect)
                        two_bit_modes => indirect_auto (pp.Literal("@") + register + pp.Literal('+'))
                                => one_bit_modes (register | indexed | absolute)
                        one_bit_modes => absolute (pp.Literal("&") + unsigned)
                            double_finishup => lista de words
        """
        def dump(s, loc, toks):
            if DEBUG: print("s: [{}]  loc: [{}]  toks: [{}]".format(s, loc, toks))


        def jmp_finishup(s, loc, toks):
            dump(s, loc, toks)
            mnem = toks[0]
            opcode = self.mnemonics[mnem][0]
            return (opcode + (toks[1] & 0x3ff), )


        def single_finishup(s, loc, toks):
            dump(s, loc, toks)
            mnem = toks[0]
            opcode = self.mnemonics[mnem][0]
            add = 0
            if toks[1][0] == "r":
                return (opcode + 0x0000 + toks[1][1], )

            elif toks[1][0] == '&':
                return (opcode + 0x0012, toks[1][1])                # Absolute

            elif toks[1][0] == 's':                                 # Symbolic
                return (opcode + 0x0010, toks[1][1])

            elif toks[1][0] == '(':
                return (opcode + 0x0010 + toks[1][2], toks[1][1])

            elif toks[1][0] == '@':
                return (opcode + 0x0020 + toks[1][1][1])

            elif toks[1][0] == '@+':
                return (opcode + 0x0030 + toks[1][1][1])

            return


        def double_finishup(s, loc, toks):
            dump(s, loc, toks)
            mnem = toks[0]
            opcode = self.mnemonics[mnem][0]
            add = 0
            # Source
            if toks[1][0] == "r":
                if toks[2][0] == "r":                               # Rn, Rn
                    return (opcode + 0x0000 + (toks[1][1] << 8) + toks[2][1], )
                elif toks[2][0] == '&':                             # Rn, &nnn
                    return (opcode + 0x0082 + (toks[1][1] << 8),
                            toks[2][1])

            elif toks[1][0] == '(':
                if toks[2][0] == "r":                               # nn(rN), Rn
                    return (opcode + 0x0010 + (toks[1][2] << 8) + toks[2][1],
                            toks[1][1])

                elif toks[2][0] == '&':                             #
                    return (opcode + 0x0092 + (toks[1][2] << 8),
                            toks[1][1],
                            toks[2][1])

                return (opcode + 0x0010 + toks[1][2], toks[1][1])

            elif toks[1][0] == '&':
                if toks[2][0] == "r":                               # &nnn, &nnn
                    return (opcode + 0x0210 + toks[2][1],
                            toks[1][1])

                elif toks[2][0] == '&':                             #
                    return (opcode + 0x0292,
                            toks[1][1],
                            toks[2][1])

            elif toks[1][0] == '@':
                if toks[2][0] == "r":                               # &nnn, &nnn
                    return (opcode + 0x0020 + (toks[1][1][1] << 8) + toks[2][1], )

                elif toks[2][0] == '&':                             #
                    return (opcode + 0x00a2 + (toks[1][1][1] << 8),
                            toks[2][1])

            elif toks[1][0] == '@+':
                if toks[2][0] == "r":                               # &nnn, &nnn
                    return (opcode + 0x0030 + (toks[1][1][1] << 8) + toks[2][1], )

                elif toks[2][0] == '&':                             #
                    return (opcode + 0x00b2 + (toks[1][1][1] << 8),
                            toks[2][1])

            elif toks[1][0] == 's':
                if toks[2][0] == "r":                               # nnn, r
                    return (opcode + 0x0010 + toks[2][1], )

                elif toks[2][0] == '&':                             #
                    return (opcode + 0x0092,
                            toks[2][1])

            elif toks[1][0] == '#':
                if toks[2][0] == "r":                               # nnn, r
                    return (opcode + 0x0030 + toks[2][1],
                            toks[1][1])

                elif toks[2][0] == '&':                             #
                    return (opcode + 0x00b2,
                            toks[1][1],
                            toks[2][1])

            else:
                print('Error en los operandos {}'.format(toks[1][0]))

            # Destination
            return


        unsigned = pp.Word(pp.nums)
        unsigned.setParseAction(lambda t: int(t[0]))
        signed = pp.Combine(pp.Optional(pp.oneOf("+ -")) + unsigned)
        signed.setParseAction(lambda t: int(t[0]))

        dot = pp.Suppress(".")
        comma = pp.Suppress(",")
        colon = pp.Suppress(":")
        par_open = pp.Suppress("(")
        par_close = pp.Suppress(")")

        label = pp.Word(pp.alphas, pp.alphanums + "_")

        # Los varios modos de direccionamiento
        register = pp.oneOf(self.reg_names)
        register.setParseAction( lambda t: ("r", self.registers[t[0]]) )

        indexed = signed + par_open + register + par_close
        indexed.setParseAction(lambda t: ("(", t[0], t[1][1]))

        indirect = pp.Literal("@") + register
        indirect.setParseAction(lambda t: ("@", t[1]))

        indirect_auto = pp.Literal("@") + register + pp.Literal('+')
        indirect_auto.setParseAction(lambda t: ('@+', t[1]))

        immediate = pp.Literal("#") + signed
        immediate.setParseAction(lambda t: ("#", t[1]))

        absolute = pp.Literal("&") + unsigned
        absolute.setParseAction(lambda t: ("&", t[1]))

        symbolic = unsigned.copy()
        symbolic.setParseAction(lambda t: ("s", int(t[0])))

        # asignando tipos de direccionamiento válidos
        one_bit_modes = register | indexed | absolute | symbolic
        two_bit_modes = one_bit_modes | indirect_auto | indirect | immediate

        single_opds = two_bit_modes
        double_opds = two_bit_modes + comma + one_bit_modes

        opc_single = pp.oneOf(self.mnem_kinds["SINGLE"], caseless = True) + single_opds
        opc_single.setParseAction(single_finishup)

        opc_double = pp.oneOf(self.mnem_kinds["DOUBLE"], caseless = True) + double_opds
        opc_double.setParseAction(double_finishup)

        opc_jump = pp.oneOf(self.mnem_kinds["JUMP"], caseless = True) + unsigned
        opc_jump.setParseAction(jmp_finishup)

        opc_noopd = pp.oneOf(self.mnem_kinds["NOOPD"], caseless = True)
        opc_noopd.setParseAction(lambda t: (self.mnemonics[t[0]][0], ))

        directive_name = pp.oneOf("text global section word end")

        code_line = (~pp.LineStart() +
                     (opc_jump | opc_single | opc_double | opc_noopd))
        directive = ~pp.LineStart() + dot + directive_name
        label_line = pp.LineStart() + label + colon

        src_line = code_line | directive | label_line        # | empty_line
        parser = pp.OneOrMore(src_line)
        return eval(which)


    def assemble_line(self, line):
        print(line)
        return self.parser.parseString(line)


    def from_source(self, fname):
        pass



def test_parser():
    memory = Memory()
    memory.reserve("ROM", 0xfc00, 1024, "R")
    memory.reserve("RAM", 0x1c00, 1024, "RW")
    memory.load_intel(PATH_PPAL + TEST_DISASM_FILE)
    asm = MSP430_assembler(memory)
    parser = asm.make_parser()
    for s in (" reti",
              " rrc r4", " RRC R4", " rrc r15",
              " mov r1, r5",
              " rra 123(r5)",
              " nop",
              " swpb @R7", " swpb @r8+",
              " sxt &123", " sxt &321",
              " sxt 123", " sxt 321",
              " sxt @r4",
              " mov #123, r4",
              " mov #123, &321",
              " jmp 1122",
              "abc_def:",
              " .text"):
        print(s, parser.parseString(s))


def test_disasm():
    memory = Memory()
    memory.reserve("ROM", 0xfc00, 1024, "R")
    memory.reserve("RAM", 0x1c00, 1024, "RW")
    memory.load_intel(TEST_DISASM_FILE)
    msp = MSP430_disassembler(memory)

    addr = 0xfc00
    while memory.initialized(addr):
        addr, line = msp.disassemble_one(addr)
        print(line)


def test_disasm_modes():
    memory = Memory()
    memory.reserve("ROM", 0xfc00, 1024, "R")
    memory.reserve("RAM", 0x1c00, 1024, "RW")
    memory.load_intel(TEST_MODES_FILE)
    msp = MSP430_disassembler(memory)

    addr = 0xfc00
    while memory.initialized(addr):
        addr, line = msp.disassemble_one(addr)
        print(line)


def test_emulation():
    memory = Memory()
    memory.reserve("ROM", 0xfc00, 1024, "R")
    memory.reserve("RAM", 0x1c00, 1024, "RW")
    memory.load_intel(PATH_PPAL + TEST_EMULATION_FILE)
    msp = MSP430_emulator(memory)
    msp.registers.dump()
    msp.single_step()
    msp.registers.dump()
    msp.single_step()
    msp.registers.dump()

    # Para que ejecute las n instrucciones dle archivo, debería hacer un memory.initialized(addr):

def test_parse_registers():
    memory = Memory()
    memory.reserve("ROM", 0xfc00, 1024, "R")
    memory.reserve("RAM", 0x1c00, 1024, "RW")
    memory.load_intel(TEST_EMULATION_FILE)
    asm = MSP430_assembler(memory)
    parser = asm.make_parser('register')
    result = parser.parseString("r12")
    print(result)

def test_registers():
    reg = Registers(0x1234, 0x1fff)
    reg.dump()


def main(args):
    #test_disasm()
    # ~ test_disasm_modes()
    # ~ test_registers()
    # ~ test_parse_registers()
    test_emulation()
    # test_parser()
    return 0

if __name__ == '__main__': # Sólo se ejecuta cuando uso la shell, o sea, como script y no como módulo
    import sys
    sys.exit(main(sys.argv)) # Devuelve lo que retorna la función main (cuando se ejecuta en la shell) --> devuelve un 0 cuando todo salió bien
