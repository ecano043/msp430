#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  memory.py
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
#   2020/11/27: Modificación a las rutinas dump y dump_words las cuales
#       ahora devuelven un string en lugar de imprimir directamente.
#       Además, si una linea no contiene 'contenido' (ie. todos los
#       lugares de memoria son None, la línea no se 'imprime'.


import pdb

TEST_FILE = "tests/test.hex"
TEST_OUTPUT_FILE = "tests/test_output.hex"

class Memory_area:
    def __init__(self, base, size, kind):
        self.base, self.size, self.kind = base, size, kind
        self.mem = [None] * self.size # Inicializo toda la memoria con None


    def get_size(self):
        return self.size


    def get_base(self):
        return self.base


    def initialized(self, addr):
        """
        Retorna true si está inicializada
        """
        return self.mem[addr - self.base] != None


    def read(self, addr, check_initialized = True):
        assert (addr - self.base) < self.size # si es false, se lanza excepción
        if check_initialized:
            assert self.initialized(addr)

        return self.mem[addr - self.base]


    def read_word(self, addr, check_initialized = True):
        assert (addr - self.base) < self.size    # Rango direccion correcto?
        assert (addr % 2) == 0                   # Direccion debe ser par, porque es word
        if check_initialized:
            assert self.initialized(addr)        # Contenido inicializado?
            assert self.initialized(addr+1)      # Contenido inicializado?

        return ( self.mem[addr   - self.base] +
                (self.mem[addr+1 - self.base] << 8))


    def write(self, addr, value):
        assert (addr - self.base) < self.size

        self.mem[addr - self.base] = value


    def write_word(self, addr, value):
        assert (addr - self.base) < self.size
        assert (addr % 2) == 0           # Direccion debe ser par

        self.mem[addr   - self.base] = value & 0xff
        self.mem[addr+1 - self.base] = value >> 8


    def range_empty(self, start, end):
        # ~ pdb.set_trace()
        for a in range(start, end):
            if self.mem[a] is not None: return False
        return True


    def dump(self):
        """ Crear el listado de la memoria (en bytes) en forma de un string
            (principalmente pensado para uso con GUI)
        """
        LINE_LENGTH = 16
        s = ''
        for addr in range(self.size):
            if self.range_empty(addr, addr + LINE_LENGTH):
                continue

            if (addr % LINE_LENGTH) == 0:
                s += "\n{:04x}: ".format(addr + self.base)

            if self.mem[addr] is None:
                s += "-- "
            else:
                s += "{:02x} ".format(self.read(addr + self.base))
        return s


    def dump_words(self):
        """ Crear el listado de la memoria (en words) en forma de un string
            (principalmente pensado para uso con GUI)
        """
        LINE_LENGTH = 16
        s = ''
        for addr in range(0, self.size, 2):
            if self.range_empty(addr, addr + LINE_LENGTH):
                continue

            if (addr % LINE_LENGTH) == 0:
                s += "\n{:04x}: ".format(addr + self.base)

            if self.mem[addr] is None:
                s += "---- "
            else:
                s += "{:04x} ".format(self.read_word(addr + self.base))
        return s

    def dump_mem_w(self):
        s = ''
        for addr in range(0, self.size, 2):
            if self.mem[addr] is None:
                s += "- - - -,"
            else:
                s += "0x{:04x} ,".format(self.read_word(addr + self.base))
                       
        return s


class Memory:
    def __init__(self):
        self.areas = {}


    def reserve(self, id, base, size, kind):
        self.areas[id] = Memory_area(base, size, kind)


    def locate_area(self, addr):
        """ Ubicar en cual area de memoria se encuentra <addr>
            Si encuentra el area, devuelve al id, sino None
        """
        for id, area in self.areas.items():
            if area.base <= addr  < area.base + area.size:
                return id
        return None


    def initialized(self, addr):
        id = self.locate_area(addr)
        assert id != None
        return self.areas[id].initialized(addr)


    def write(self, addr, byte):
        id = self.locate_area(addr)
        assert id != None
        self.areas[id].write(addr, byte)


    def read_word(self, addr, check_initialized = True):
        id = self.locate_area(addr)
        assert id != None # assertion si es None
        return self.areas[id].read_word(addr, check_initialized)


    def write_word(self, addr, w):
        id = self.locate_area(addr)
        assert id != None
        return self.areas[id].write_word(addr, w)


    def next_code_address(self, id, addr):
        addr += 2
        area = self.areas[id]
        if addr < area.base + area.size:
            return addr
        else:
            return None


    def checksum(self, s):
        """ s por ejemplo contiene 10010000214601360121470136007EFE09D2190140
            Esta rutina suma todos los bytes de la linea
            y devuelve la suma modulo 256.
        """
        sum = 0
        for i in range(0, len(s), 2):
            sum += int(s[i:i+2], 16)
        return sum & 0xff


    def load_intel(self, filename):
        with open(filename) as intelf:
            for line in intelf:
                line = line.rstrip('\n')

                # Todas las lineas deben empezar con ':'
                if line[0] != ":":
                    exit(1)
                # Controlar si la linea tiene datos validos
                if self.checksum(line[1:]) != 0:
                    print("Error checksum en {}".format(line))
                    print("Esperaba: " +
                        "{:02x}".format((0 - self.checksum(line[1:-2])) & 0xff))
                    exit(1)

                nrbytes = int(line[1:3], 16)
                address = int(line[3:7], 16)
                kind = int(line[7:9], 16)
                if kind == 1:
                    break
                elif kind == 3:
                    continue

                for i in range(nrbytes):
                    self.write(address, int(line[9 + i*2 : 11 + i*2], 16))
                    address += 1


    def save_intel(self, id, filename):
        area = self.areas[id]
        with open(filename, "w") as intelf:
            for addr in range(area.base, area.base + area.size):
                if area.initialized(addr):
                    s = ":01{:04x}00{:02x}".format(addr, area.read(addr))
                    s += "{:02x}\n".format((256 - self.checksum(s[1:])) & 0xff)
                    intelf.write(s)
            intelf.write(":00000001ff\n")


    def dump(self, id):
        area = self.areas[id]
        s = "\nid: {}, base: 0x{:04x}, size: {}, flags: {}\n".format(
                    id, area.base, area.size, area.kind)
        return s + area.dump()


    def dump_words(self, id):
        area = self.areas[id]
        s = "\nid: {}, base: 0x{:04x}, size: {}, flags: {}\n".format(
                    id, area.base, area.size, area.kind)
        return s + area.dump_words()

    def dump_mem(self, id):
        area = self.areas[id]
        return area.dump_mem_w()



def test_checksum():
    m = Memory()
    sum = m.checksum("10010000214601360121470136007EFE09D2190140")
    print(sum)


def test_load():
    SIZE = 1024
    m = Memory()
    m.reserve("ROM", 0x10000 - SIZE, SIZE, "R")
    m.load_intel("tests/test.hex")
    print(m.dump("ROM"))
    print(m.dump_words("ROM"))


def test_save():
    SIZE = 1024
    m = Memory()
    m.reserve("ROM", 0x10000 - SIZE, SIZE, "R")
    m.load_intel(TEST_FILE)
    m.save_intel("ROM", TEST_OUTPUT_FILE)
    print(m.dump("ROM"))


def main(args):
    # ~ test_checksum()
    test_load()
    # ~ test_save()
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
