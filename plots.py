#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import formula
import converters
from OpenGL.GL import *
from OpenGL.GLU import *

class Plots:
    def on_destroy(self, *args):
        Gtk.main_quit()

    def key_pressed(self, widget, event):
        pass

    def main(self):
        builder = Gtk.Builder()
        builder.add_from_file("plots.glade")
        builder.connect_signals(self)

        self.window = builder.get_object("main_window")
        self.scroll = builder.get_object("equation_scroll")
        self.formula_box = builder.get_object("equation_box")
        self.gl_area = builder.get_object("gl")
        self.gl_area.connect("render", self.gl_render)

        for c in self.formula_box.get_children():
            self.formula_box.remove(c)

        self.formulae = [formula.Editor()]
        self.formula_box.pack_start(self.formulae[0], False, False, 0)

        self.window.set_default_size(600,400)
        self.window.show_all()

        Gtk.main()

    def gl_render(self, area, context):
        area.make_current()
        w = area.get_allocated_width()
        h = area.get_allocated_height()
        glViewport(0, 0, w, h)

        glClearColor(1, 0, 1, 0)
        glClear(GL_COLOR_BUFFER_BIT)

        return True

if __name__ == '__main__':
    Plots().main()
