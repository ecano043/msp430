#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  profile_instr_lookup.py
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
#

from msp430 import MSP430, MSP430_assembler, TEST_DISASM_FILE
from memory import Memory
from random import choice
import pyparsing as pp
import cProfile
import sys

def make_parser(opcs):
    return pp.oneOf(opcs)

def time_by_dict():
    memory = Memory()
    memory.reserve("ROM", 0xfc00, 1024, "R")
    memory.reserve("RAM", 0x1c00, 1024, "RW")
    memory.load_intel(TEST_DISASM_FILE)

    asm = MSP430_assembler(memory)
    test_set = list(asm.xref.keys())
    # ~ for i in range(1000000):
        # ~ opc = choice(test_set)
        # ~ opc in asm.xref
        # ~ try:
            # ~ asm.xref[opc]
        # ~ except:
            # ~ pass

    test_set = list(asm.xref.keys())
    parser = make_parser(' '.join(test_set))
    # ~ print(parser)
    for i in range(1000000):
        parser.parseString(choice(test_set))

def main(argv):
    time_by_dict()
    return 0

main(sys.argv)
