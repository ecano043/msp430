#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  gui_text.py
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
#   2020/10/05:
#       Corregido - problemas con acceso a memoria
#       Agregado 'ram'
#       Implementado comando de registers
#   2020/10/08:
#       Comando 'r' acepta como primer argumento el nombre de una bandera de
#           Flags y setea su valor (0 if argumento 2 es 0, sino 1)
#       Faltaba convertir argumento 2 a entero para que funcione
#       Banderas 'CPU OFF', y 'OSC OFF' fueron renombrados a 'NCPU' y 'NOSC'
#           para evitar problemas con la interpretación del número de argumentos
#   2020/11/27:
#       Modificacion de dump y dump_words en memory.py requirio modificacion
#       en las llamadas.

from memory import Memory
from msp430 import MSP430_disassembler, MSP430_emulator, MSP430_assembler
import pdb, os

VERSION = "0.3"
PATH_PPAL = os.path.dirname(os.path.abspath(__file__)) + "/"
DEFAULT_INPUT = PATH_PPAL + "tests/test.hex"


def help():
    print("lf <archivo>         Cargar archivo intel\n"
          "a <addr> mnem [opds] Ensamblar una línea\n"
          "m [<id>]             Mostrar memoria en bytes (area <id>)\n"
          "mw [<id>]            Mostrar memoria en words (area <id>)\n"
          "d                    Desensamblar memoria\n"
          "n                    Ejecutar una linea de codigo\n"
          "s                    Ejecutar una instrucción\n"
          "r                    Ver registros\n"
          "r <reg> <valor>      Modificar registros. <reg> válidos son: \n"
          "                     C, Z, N, V, NCPU, NOSC, GIE, SCG1, SCG2\n"
          "r <flag> <valor>     Modificar bits en el Status\n"
          "h | help | ?         Ayuda (este texto)\n"
          "q                    Terminar al programa\n")


def commands():
    """ Lazo de comandos: Instanciar una CPU, luego pedir instrucciones al
        usuario y ejecutarlos """
    def cmd_lf(parts):
        if len(parts) != 2:
            print('Comando "lf" necesita el nombre del archivo')
            return
        memory.load_intel(parts[1])

    COMMANDS = {"lf": cmd_lf}

    memory = Memory()
    memory.reserve("ROM", 0xfc00, 1024, "R")
    memory.load_intel(DEFAULT_INPUT)
    memory.reserve("RAM", 0x1c00, 1024, "RW")
    cpu = MSP430_disassembler(memory)
    emu = MSP430_emulator(memory)
    asm = MSP430_assembler(memory)

    while True:
        line = input("--> ")
        parts = line.split()
        if parts == []:
            continue

        if parts[0] in COMMANDS:
            COMMANDS[parts[0]](parts)

        elif parts[0] == "a":
            if len(parts) < 3:
                print('Comando "a" necesita dirección y código')
                continue
            try:
                addr = int(parts[1], 0)
            except:
                print("Esperaba un valor numérico para la dirección")
                continue
            source = ' '.join(parts[2:])
            result = asm.assemble_line(' ' + source)
            print("Result:", result)
            for w in result[0]:
                memory.write_word(addr, w)
                addr += 2

        elif parts[0] == "lf":
            if len(parts) != 2:
                print('Comando "lf" necesita el nombre del archivo')
                continue
            print(memory.load_intel(parts[1]))

        elif parts[0] == "m":
            if len(parts) == 2:
                print(memory.dump(parts[1]))
            else:
                for area in memory.areas:
                    print(memory.dump(area))

        elif parts[0] == "mw":
            if len(parts) == 2:
                print(memory.dump_words(parts[1]))
            else:
                for area in memory.areas:
                    print(memory.dump_words(area))

        elif parts[0] == "d":
            addr = 0xfc00
            while addr <= 0xffff:
                if memory.initialized(addr):
                    new_addr, s = cpu.disassemble_one(addr)
                    print("{:04x}  {}".format(addr, s))
                    addr = new_addr
                else:
                    addr = memory.next_code_address("ROM", addr)
                if addr is None:
                    break

        elif parts[0] == "r":
            if len(parts) == 1:
                cpu.registers.dump()
            elif len(parts) == 3:
                try:
                    bit = cpu.registers.FL_BITS.index(parts[1].upper())
                    cpu.registers.set_flag(bit, int(parts[2]) != 0)
                except:
                    cpu.registers.set_reg(int(parts[1]), int(parts[2], 0))
                cpu.registers.dump()
            else:
                print('Comando "r" espera 0 o 2 argumentos')

        elif parts[0] == "s":
            emu.single_step()
            emu.registers.dump()

        elif parts[0] == "q":
            break

        elif parts[0] in ("h", "help", "?"):
            help()

        else:
            print("Comando invalido (h para ayuda):", line)



def main(args):
    print("Herramientas para el MSP430 v", VERSION)
    commands()
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))

