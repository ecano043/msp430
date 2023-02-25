#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  msp_gui.py
#
#  Copyright 2020 Roberto Leonel Pacha <rpacha731@alumnos.iua.edu.ar>
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

import gi, os, time, subprocess
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gtk, GtkSource
from msp430 import MSP430_assembler, MSP430_disassembler, MSP430_emulator
from memory import Memory

MAIN_TITLE = "Herramientas de Desarrollo para MSP430"
VERSION = "1.0"
PATH_PPAL = os.path.dirname(os.path.abspath(__file__)) + "/"
ICON_PATH = "icons/"
DEFAULT_INPUT = "tests/test.hex"

memory = Memory()
memory.reserve("ROM", 0xfc00, 1024, "R")
memory.load_intel(PATH_PPAL + DEFAULT_INPUT)
memory.reserve("RAM", 0x1c00, 1024, "RW")
mspEMU = MSP430_emulator(memory)
mspDIS = MSP430_disassembler(memory)
mspASS = MSP430_assembler(memory)
ejecutar = True


class MainMenu(Gtk.MenuBar):
    def __init__(self, toplevel):
        super(MainMenu, self).__init__()
        self.main_menu = {}
        self.toplevel = toplevel

        for key in ["Archivo", "Editar", "Herramientas", "Ayuda"]:
            item = Gtk.MenuItem(label = key)
            self.main_menu[key] = Gtk.Menu()
            item.set_submenu(self.main_menu[key])
            self.add(item)

        self.add_items_to("Archivo", (("Quit", lambda x: Gtk.main_quit()), ))
        self.add_items_to("Ayuda", (("About", self.on_about_activated), ))


    def add_items_to(self, main_item, items):
        for item, handler in items:
            if item == None:
                it = Gtk.SeparatorMenuItem()
            else:
                it = Gtk.ImageMenuItem(label = item)
                it.connect("activate", handler)
            self.main_menu[main_item].insert(it, 0)


    def on_about_activated(self, menuitem):
        logo = GdkPixbuf.Pixbuf.new_from_file(PATH_PPAL + ICON_PATH + "micro.png")
        dlg = Gtk.AboutDialog(version = VERSION,
                              program_name = MAIN_TITLE,
                              logo = logo,
                              license_type = Gtk.License.GPL_3_0,
                              authors = ["Roberto Leonel Pacha"])
        dlg.set_transient_for(self.toplevel)
        dlg.run()
        dlg.destroy()


class Emulator(Gtk.Frame):
    def __init__(self, toplevel):
        self.toplevel = toplevel
        super(Emulator, self).__init__()

        self.fixed = Gtk.Fixed()

        self.tools = self.make_tools()
        self.mem_view = self.make_memory_viewer()
        self.reg_view = self.make_register_viewer()
        self.emu_view = self.make_emulator_viewer()
        self.flags_view = self.make_flags_viewer()
        self.file_intel = self.make_file_intel()
        self.modify_reg = Gtk.Switch(active = False, tooltip_text = "Modificar Registros")
        self.modify_reg.connect("notify::active", self.swit)
        self.save_regs = Gtk.Button(label = "Guardar registros", sensitive = False)
        self.save_regs.connect("clicked", self.saving_regs)
        icon = GdkPixbuf.Pixbuf.new_from_file_at_size(PATH_PPAL + ICON_PATH + "micro.png", 50, 50)
        img = Gtk.Image.new_from_pixbuf(icon)

        self.fixed.put(img, 450, 11)
        self.fixed.put(self.tools, 5, 0)
        self.fixed.put(self.emu_view, 5, 65)
        self.fixed.put(self.reg_view, 5, 515)
        self.fixed.put(self.flags_view, 520, 0)
        self.fixed.put(self.mem_view, 710, 0)
        self.fixed.put(self.file_intel, 200, 696)
        self.fixed.put(self.modify_reg, 5, 700)
        self.fixed.put(self.save_regs, 470, 696)
        m = Gtk.Label(label = "")
        m.set_markup("<u>Modificar Registros</u>")
        self.fixed.put(m, 60, 703)
        me = Gtk.Label(label = "")
        me.set_markup("<u>Cargar Archivo .hex en Memoria</u>")
        self.fixed.put(me, 245, 703)

        self.add(self.fixed)


    def make_file_intel(self):
        pxb = GdkPixbuf.Pixbuf.new_from_file_at_size(PATH_PPAL + ICON_PATH + "intel_file.png", 20, 20)
        img = Gtk.Image.new_from_pixbuf(pxb)
        btn = Gtk.Button(image = img, tooltip_text = "Cargar un archivo .hex en memoria")
        btn.connect("clicked", self.clicked)
        return btn


    def swit(self, switch, active):
        for i in range(len(self.regval)):
            self.regval[i].set_properties(editable = True)
        for i in range(len(self.flagval)):
            self.flagval[i].set_properties(editable = True)
        self.save_regs.set_properties(sensitive = True)

    
    def saving_regs(self, btn):
        for i in range(len(self.regval)):
            self.regval[i].set_properties(editable = False)
            mspEMU.registers.set_reg(i, int(self.regval[i].get_text().replace("0x", ""), 16))
        for i in range(len(self.flagval)):
            self.flagval[i].set_properties(editable = False)
            mspEMU.registers.set_flag(i, int(self.flagval[i].get_text().replace("0x", ""), 16))
        self.refresh_regs()
        self.modify_reg.set_active(False)
        self.save_regs.set_properties(sensitive = False)


    def clicked(self, btn):
        fc = Gtk.FileChooserDialog(action = Gtk.FileChooserAction.OPEN)

        for glob, title in (("*.hex", "Intel hex binaries (*.hex)"),
                            ("*", "All files (*)")):
            filt = Gtk.FileFilter()
            filt.add_pattern(glob)
            filt.set_name(title)
            fc.add_filter(filt)

        fc.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                       "Ok", Gtk.ResponseType.OK)

        if fc.run() == Gtk.ResponseType.OK:
            fname = fc.get_filename()
            mspEMU.memory.load_intel(fname)
            self.refresh_memory()
            self.reset()

        fc.destroy()


    def make_tools(self):
        frame = Gtk.Frame(label = "Control")

        hbox = Gtk.HBox(spacing = 4)
        self.btns = {}
        self.escala = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 10, 1)
        for fname, hint, sensitive, handler in (
                    ("play.png",  "Step",  True,  self.on_step),
                    ("rapido.png", "Run",   True,  self.on_run),
                    ("pause.png", "Pause", True, self.on_pause),
                    ("stop.png",  "Stop",  True, self.on_stop),
                    ("reset.png", "Reset", True,  self.on_reset)):
            pxb = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        PATH_PPAL + ICON_PATH + fname, 30, 30)
            img = Gtk.Image.new_from_pixbuf(pxb)
            btn = Gtk.Button(
                        tooltip_text = hint,
                        sensitive = sensitive)
            btn.set_image(img)
            btn.connect("clicked", handler)
            self.btns[hint] = btn
            hbox.pack_start(btn, False, False, 0)

        hbox.pack_start(self.escala, True, True, 0)
        frame.add(hbox)
        frame.set_size_request(425, 55)
        return frame


    def make_memory_viewer(self):
        frame = Gtk.Frame(label = "Memoria")

        grid = Gtk.Grid(column_spacing = 5)
        scroller = Gtk.ScrolledWindow()
        scroller.add(grid)
        sep = Gtk.VSeparator()

        gridRAM = Gtk.Grid(row_spacing = 5,
                           column_spacing = 5)
        
        gridROM = Gtk.Grid(row_spacing = 5,
                           column_spacing = 5)
        
        lblRAM = Gtk.Label(label = "MEMORIA RAM")
        lblRAM.set_markup('<span foreground="red"><u>MEMORIA RAM</u></span>')
        gridRAM.attach(lblRAM, 1, 0, 1, 1)
        lblROM = Gtk.Label(label = "MEMORIA ROM")
        lblROM.set_markup('<span foreground="red"><u>MEMORIA ROM</u></span>')
        gridROM.attach(lblROM, 1, 0, 1, 1)

        self.cellRAM = [Gtk.Label(label = "- - - -") for _ in range(513)]
        self.cellROM = [Gtk.Label(label = "- - - -") for _ in range(513)]

        baseROM = mspEMU.memory.areas["ROM"].base
        baseRAM = mspEMU.memory.areas["RAM"].base

        for g in range(512):
            lbl = Gtk.Label(label = "{:04x}".format(baseRAM))
            baseRAM += 2
            gridRAM.attach(lbl, 0, g + 1, 1, 1)
            gridRAM.attach(self.cellRAM[g], 1, g + 1, 1, 1)

        for g in range(512):
            lbl = Gtk.Label(label = "{:04x}".format(baseROM))
            baseROM += 2
            gridROM.attach(lbl, 0, g + 1, 1, 1)
            gridROM.attach(self.cellROM[g], 1, g + 1, 1, 1)        

        grid.attach(gridRAM, 0, 0, 1, 1)
        grid.attach(sep, 1, 0, 1, 1)
        grid.attach(gridROM, 2, 0, 1, 1)
        self.refresh_memory()
        frame.add(scroller)
        frame.set_size_request(305, 515)

        return frame


    def refresh_memory(self):
        s = mspEMU.memory.dump_mem("ROM").split(",")
        for i in range(len(s)):
            self.cellROM[i].set_properties(label = s[i])

        e = mspEMU.memory.dump_mem("RAM").split(",")
        for i in range(len(e)):
            self.cellRAM[i].set_properties(label = e[i])


    def make_register_viewer(self):
        frame = Gtk.Frame(label = "Registros")
        
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(5)

        reg = [Gtk.Label(label = "") for _ in range(16)]
        self.regval = [Gtk.Entry(text = "") for _ in range(16)]

        for i in range(16):
            reg[i] = Gtk.Label(label = mspEMU.registers.NAMES[i] + " = ")

        for i in range(4):
            ia = i*4
            self.regval[ia] = Gtk.Entry(text = "0x{:04x}".format(mspEMU.registers.get_reg(ia)), editable = False)     
            self.regval[ia+1] = Gtk.Entry(text = "0x{:04x}".format(mspEMU.registers.get_reg(ia+1)), editable = False)
            self.regval[ia+2] = Gtk.Entry(text = "0x{:04x}".format(mspEMU.registers.get_reg(ia+2)), editable = False)
            self.regval[ia+3] = Gtk.Entry(text = "0x{:04x}".format(mspEMU.registers.get_reg(ia+3)), editable = False)      

            grid.attach(reg[ia], 0, i, 1, 1)
            grid.attach(reg[ia+1], 2, i, 1, 1)
            grid.attach(reg[ia+2], 4, i, 1, 1)
            grid.attach(reg[ia+3], 6, i, 1, 1)
            grid.attach(self.regval[ia], 1, i, 1, 1)
            grid.attach(self.regval[ia+1], 3, i, 1, 1)
            grid.attach(self.regval[ia+2], 5, i, 1, 1)
            grid.attach(self.regval[ia+3], 7, i, 1, 1)

        frame.add(grid)
        frame.set_size_request(1010, 177)
        return frame


    def make_flags_viewer(self):
        frame = Gtk.Frame(label = "Banderas")
        regs = mspEMU.registers

        grid = Gtk.Grid()
        grid.set_row_spacing(2)

        flag = [Gtk.Label(label = "") for _ in range(9)]
        self.flagval = [Gtk.Entry(text = "") for _ in range(9)]

        grid.attach(Gtk.Label(label = " "), 0, 0, 1, 18)
        grid.attach(Gtk.Label(label = " "), 1, 0, 1, 18)

        for i in range(9):
            flag[i] = Gtk.Label(label = regs.FL_BITS[i] + " = ")
            self.flagval[i] = Gtk.Entry(text = "{:d}".format(regs.get_flag(0)), editable = False)     
            grid.attach(flag[i], 2, i*2, 1, 1)
            grid.attach(self.flagval[i], 2, (i*2)+1, 1, 1)

        frame.add(grid)
        frame.set_size_request(181, 515)
        return frame    


    def refresh_regs(self):
        for i in range(16):
            self.regval[i].set_properties(text = "0x{:04x}".format(mspEMU.registers.get_reg(i)), editable = False)
        for i in range(9):
            self.flagval[i].set_properties(text = "{:d}".format(mspEMU.registers.get_flag(i)), editable = False)


    def make_emulator_viewer(self):
        frame = Gtk.Frame(
                    label = "Emulator",
                    hexpand = False,
                    vexpand = False)
        self.emu_buffer = Gtk.TextBuffer()
        self.emu_viewer = Gtk.TextView(
                    buffer = self.emu_buffer)

        scroller = Gtk.ScrolledWindow()
        scroller.add(self.emu_viewer)
        frame.add(scroller)
        frame.set_size_request(505, 450)

        return frame


    def emulator_add_text(self, text):
        self.emu_buffer.insert(
                    self.emu_buffer.get_end_iter(), text)
    

    def emulator_clear_text(self):
        start = self.emu_buffer.get_start_iter()
        end = self.emu_buffer.get_end_iter()
        self.emu_buffer.delete(start, end)


    def on_step(self, btn):
        regs = mspEMU.registers
        esc = int(self.escala.get_value())
        for _ in range(esc):
            addr, s = mspDIS.disassemble_one(regs.get_reg(regs.PC))
            mspEMU.single_step()
            self.refresh_regs()
            self.emulator_add_text(s + "\n")
        # time.sleep(1)


    def on_pause(self, btn):
        ejecutar = False


    def on_run(self, btn):
        # hilo = threading.Thread(target=self.ejec, daemon=True)
        # hilo.start()
        while ejecutar:
            self.ejec()
            
            if ejecutar is False:
                break


    def ejec(self):
        regs = mspEMU.registers
        addr, s = mspDIS.disassemble_one(regs.get_reg(regs.PC))
        mspEMU.single_step()
        self.refresh_regs()
        self.emulator_add_text(s + "\n")
        time.sleep(1)


    def on_reset(self, btn):
        regs = mspEMU.registers
        ram = memory.areas["RAM"]
        regs.set_reg(regs.PC, memory.read_word(0xfffe))
        regs.set_reg(regs.SP, (ram.base + ram.size))
        self.emulator_clear_text()
        self.escala.set_value(0)


    def reset(self):
        regs = mspEMU.registers
        ram = memory.areas["RAM"]
        regs.set_reg(regs.PC, memory.read_word(0xfffe))
        regs.set_reg(regs.SP, (ram.base + ram.size))
        self.emulator_clear_text()
        self.escala.set_value(0)


    def on_stop(self, btn):
        self.reset()



class MainWindow(Gtk.Window):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.connect("destroy", lambda x: Gtk.main_quit())
        self.set_title(MAIN_TITLE)
        self.set_properties(icon = GdkPixbuf.Pixbuf.new_from_file(PATH_PPAL + ICON_PATH + "/micro.png"),
                            title = MAIN_TITLE,
                            resizable = False)
        self.set_default_size(1033, 808)
        self.hexviewer = None

        vbox = Gtk.VBox()

        # Agregar el menu principal
        mainmenu = MainMenu(self)
        mainmenu.add_items_to("Archivo", (
                ("Guardar hex file como ...", self.on_save_hex_as),
                ("Abrir hex file ...", self.on_open_hex),
                ("Guardar source (asm) file como ...", self.on_save_source_as),
                ("Abrir source (asm) file ...", self.on_open_source)))

        mainmenu.add_items_to("Herramientas", (("Make", self.make), ))

        # mainmenu.add_items_to("Editar", (("Make", self.make), ))

        vbox.pack_start(mainmenu, False, False, 0)
        # Agregar notebook con editor y imagen
        self.nb = Gtk.Notebook(margin = 4)
        vbox.pack_start(self.nb, True, True, 0)

        # Creamos al editor con su 'cuadro' y lo agregamos a la notebook
        frame = Gtk.Frame(
                    label = "Editor",
                    margin = 4)
        self.edit_buffer = GtkSource.Buffer()
        editor = GtkSource.View(
                    name = "code",
                    buffer = self.edit_buffer)
        edit_scroller = Gtk.ScrolledWindow()
        edit_scroller.add(editor)
        frame.add(edit_scroller)

        self.nb.append_page(frame, Gtk.Label(label = "Editor"))

        # Creamos la pestaña para el emulador
        self.emulator = Emulator(self)
        self.nb.append_page(self.emulator, Gtk.Label(label = "Emulator"))

        self.add(vbox)
        self.show_all()

    
    def make(self, menuitem):
        subprocess.call(("cd " + PATH_PPAL + " && make"), shell=True)


    def create_hex_page(self):
        frame = Gtk.Frame(
                    label = "Hex viewer",
                    margin = 6)
        self.tbuffer = Gtk.TextBuffer()
        viewer = Gtk.TextView(
                    buffer = self.tbuffer,
                    editable = True)
        scroller = Gtk.ScrolledWindow(
                    margin = 4)
        scroller.add(viewer)
        frame.add(scroller)
        frame.show_all()

        return frame


    def on_open_source(self, menuitem):
        """ Abrir un archivo fuente (*.asm)
        """
        fc = Gtk.FileChooserDialog(
                    parent = self,
                    action = Gtk.FileChooserAction.OPEN)

        for glob, title in (("*.asm", "Assembler source files (*.asm)"),
                            ("*", "All files (*)")):
            filt = Gtk.FileFilter()
            filt.add_pattern(glob)
            filt.set_name(title)
            fc.add_filter(filt)

        fc.add_buttons(
                    "Cancel", Gtk.ResponseType.CANCEL,
                    "Ok", Gtk.ResponseType.OK)

        if fc.run() == Gtk.ResponseType.OK:
            fname = fc.get_filename()
            with open(fname) as infile:
                text = infile.read()
            self.edit_buffer.set_text(text)

        fc.destroy()


    def on_save_source_as(self, menuitem):
        """ Guardar el texto en el editor a disco, a un archivo *.asm
        """
        fc = Gtk.FileChooserDialog(
                    parent = self,
                    do_overwrite_confirmation = True,
                    action = Gtk.FileChooserAction.SAVE)

        for glob, title in (("*.asm", "Assembler source files (*.asm)"),
                            ("*", "All files (*)")):
            filt = Gtk.FileFilter()
            filt.add_pattern(glob)
            filt.set_name(title)
            fc.add_filter(filt)

        fc.add_buttons(
                    "Cancel", Gtk.ResponseType.CANCEL,
                    "Save", Gtk.ResponseType.OK)

        if fc.run() == Gtk.ResponseType.OK:
            fname = fc.get_filename() + ".asm"
            with open(fname, "w") as outfile:
                text = self.edit_buffer.get_text(
                            self.edit_buffer.get_start_iter(),
                            self.edit_buffer.get_end_iter(),
                            False)
                outfile.write(text)

        fc.destroy()


    def on_open_hex(self, menuitem):
        """ Abrir un archivo fuente (*.asm)
        """
        fc = Gtk.FileChooserDialog(
                    parent = self,
                    action = Gtk.FileChooserAction.OPEN)

        for glob, title in (("*.hex", "Intel hex binaries (*.hex)"),
                            ("*", "All files (*)")):
            filt = Gtk.FileFilter()
            filt.add_pattern(glob)
            filt.set_name(title)
            fc.add_filter(filt)

        fc.add_buttons(
                    "Cancel", Gtk.ResponseType.CANCEL,
                    "Ok", Gtk.ResponseType.OK)

        if fc.run() == Gtk.ResponseType.OK:
            fname = fc.get_filename()
            if self.hexviewer is None:
                self.hexviewer = self.create_hex_page()
                self.nb.append_page(
                            self.hexviewer,
                            Gtk.Label(label = "Hex"))
                with open(fname) as infile:
                    text = infile.read()
                self.tbuffer.set_text(text)
            else:
                with open(fname) as infile:
                    text = infile.read()
                self.tbuffer.set_text(text)

        fc.destroy()


    def on_save_hex_as(self, menuitem):
        """ Guardar el texto en el editor a disco, a un archivo *.asm
        """
        fc = Gtk.FileChooserDialog(
                    parent = self,
                    do_overwrite_confirmation = True,
                    action = Gtk.FileChooserAction.SAVE)

        for glob, title in (("*.hex", "Intel hex binaries (*.hex)"),
                            ("*", "All files (*)")):
            filt = Gtk.FileFilter()
            filt.add_pattern(glob)
            filt.set_name(title)
            fc.add_filter(filt)

        fc.add_buttons(
                    "Cancel", Gtk.ResponseType.CANCEL,
                    "Save", Gtk.ResponseType.OK)

        if fc.run() == Gtk.ResponseType.OK:
            fname = fc.get_filename() + ".hex"
            with open(fname, "w") as outfile:
                text = self.tbuffer.get_text(
                    self.tbuffer.get_start_iter(),
                    self.tbuffer.get_end_iter(),
                    False)
                outfile.write(text)

        fc.destroy()


    def run(self):
        Gtk.main()



def main(args):
    mainwdw = MainWindow()
    mainwdw.run()
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
