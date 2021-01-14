#!/usr/bin/env python3

# Copyright 2021 Alexander Huntley

# This file is part of Plots.

# Plots is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Plots is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Plots.  If not, see <https://www.gnu.org/licenses/>.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf

from plots import formula
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
from jinja2 import Environment, FileSystemLoader, PackageLoader
import sys
import importlib.resources

import numpy as np

class Plots(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.github.alexhuntley.Plots")
        self.scale = 10
        self.translation = np.array([0, 0], 'f')
        self.jinja_env = Environment(loader=PackageLoader('plots', 'shaders'))
        self.vertex_template = self.jinja_env.get_template('vertex.glsl')
        self.fragment_template = self.jinja_env.get_template('fragment.glsl')
        self.formulae = []

    def key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            self.add_equation(None)
            return

    def do_activate(self):
        builder = Gtk.Builder()
        builder.add_from_string(read_ui_file("plots.glade"))
        builder.connect_signals(self)

        self.window = builder.get_object("main_window")
        self.add_window(self.window)
        loader = GdkPixbuf.PixbufLoader()
        loader.write(importlib.resources.read_binary("plots.res", "com.github.alexhuntley.Plotter.svg"))
        loader.close()
        self.window.set_icon(loader.get_pixbuf())
        self.window.set_title("Plots")
        self.scroll = builder.get_object("equation_scroll")
        self.formula_box = builder.get_object("equation_box")
        self.add_equation_button = builder.get_object("add_equation")
        self.window.connect("key-press-event", self.key_pressed)

        self.gl_area = builder.get_object("gl")
        self.gl_area.connect("render", self.gl_render)
        self.gl_area.connect("realize", self.gl_realize)

        self.add_equation_button.connect("clicked", self.add_equation)

        menu_button = builder.get_object("menu_button")

        self.menu = Gio.Menu()
        self.menu.append("Help", "app.help")
        self.menu.append("About Plots", "app.about")
        menu_button.set_menu_model(self.menu)

        self.about_action = Gio.SimpleAction.new("about", None)
        self.about_action.connect("activate", self.about_cb)
        self.about_action.set_enabled(True)
        self.add_action(self.about_action)

        help_action = Gio.SimpleAction.new("help", None)
        help_action.connect("activate", self.help_cb)
        help_action.set_enabled(True)
        self.add_action(help_action)

        for c in self.formula_box.get_children():
            self.formula_box.remove(c)

        self.add_equation(None)

        self.window.set_default_size(1280,720)
        self.window.show_all()

        self.drag = Gtk.GestureDrag(widget=self.gl_area)
        self.drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.drag.connect("drag-update", self.drag_update)
        self.drag.connect("drag-begin", self.drag_begin)
        self.gl_area.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.gl_area.connect('scroll_event', self.scroll_zoom)

    def gl_render(self, area, context):
        area.make_current()
        w = area.get_allocated_width() * area.get_scale_factor()
        h = area.get_allocated_height() * area.get_scale_factor()
        self.viewport = np.array([w, h], 'f')
        graph_extent = 2*self.viewport/self.viewport[0]*self.scale
        # extent of each pixel, in graph coordinates
        pixel_extent = graph_extent / self.viewport
        glViewport(0, 0, w, h)

        glClearColor(0, 0, 1, 0)
        glClear(GL_COLOR_BUFFER_BIT)

        shaders.glUseProgram(self.shader)
        glUniform2f(glGetUniformLocation(self.shader, "viewport"), *self.viewport)
        glUniform2f(glGetUniformLocation(self.shader, "translation"), *self.translation)
        glUniform2f(glGetUniformLocation(self.shader, "pixel_extent"), *pixel_extent)
        glUniform1f(glGetUniformLocation(self.shader, "scale"), self.scale)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, 18)
        glBindVertexArray(0)

        return True

    def gl_realize(self, area):
        area.make_current()

        if (area.get_error() != None):
            return

        self.vertex_shader = shaders.compileShader(
            self.vertex_template.render(), GL_VERTEX_SHADER)
        self.update_shader()

        self.vbo = vbo.VBO(np.array([
            [-1, -1, 0],
            [-1, 1, 0],
            [1, 1, 0],
            [-1, -1, 0],
            [1, -1, 0],
            [1, 1, 0]
        ],'f'), usage="GL_STATIC_DRAW_ARB")

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        self.vbo.bind()
        self.vbo.copy_data()
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3*self.vbo.data.itemsize, self.vbo)
        glEnableVertexAttribArray(0)
        self.vbo.unbind()
        glBindVertexArray(0)

    def drag_update(self, gesture, dx, dy):
        dr = 2*np.array([dx, -dy], 'f')/self.viewport[0]*self.gl_area.get_scale_factor()
        self.translation = self.init_translation + dr*self.scale
        self.gl_area.queue_draw()

    def drag_begin(self, gesture, start_x, start_y):
        self.init_translation = self.translation

    def scroll_zoom(self, widget, event):
        _, dx, dy = event.get_scroll_deltas()
        self.scale *= np.exp(dy/10)
        widget.queue_draw()

    def formula_edited(self, widget):
        self.update_shader()
        self.gl_area.queue_draw()

    def formula_cursor_position(self, widget, x, y):
        adj = widget.get_parent().get_hadjustment().props
        adj.upper = widget.get_size_request()[0]
        if x - 4 < adj.value:
            adj.value = x - 4
        elif x + 4 > adj.value + adj.page_size:
            adj.value = x - adj.page_size + 4

    def update_shader(self):
        exprs = []
        for f in self.formulae:
            body, expr = f.expr.to_glsl()
            if expr:
                exprs.append((body, expr))
        try:
            fragment_shader = shaders.compileShader(
                self.fragment_template.render(formulae=exprs),
                GL_FRAGMENT_SHADER)
        except shaders.ShaderCompilationError as e:
            print(e.args[0])
            fragment_shader = shaders.compileShader(
                self.fragment_template.render(formulae=[]),
                GL_FRAGMENT_SHADER)
            #print(e.args[1][0].decode())
        self.shader = shaders.compileProgram(self.vertex_shader, fragment_shader)


    def add_equation(self, _):
        builder = Gtk.Builder()
        builder.add_from_string(read_ui_file("formula_box.glade"))
        builder.connect_signals(self)
        formula_box = builder.get_object("formula_box")
        delete_button = builder.get_object("delete_button")
        viewport = builder.get_object("editor_viewport")
        editor = formula.Editor()

        editor.connect("edit", self.formula_edited)
        editor.connect("cursor_position", self.formula_cursor_position)
        delete_button.connect("clicked", self.delete_equation, editor)
        viewport.add(editor)
        formula_box.show_all()
        self.formula_box.pack_start(formula_box, False, False, 0)
        editor.grab_focus()
        self.formulae.append(editor)

    def delete_equation(self, widget, editor):
        self.formulae.remove(editor)
        widget.get_parent().destroy()
        if not self.formulae:
            self.add_equation(None)
        self.update_shader()
        self.gl_area.queue_draw()

    def about_cb(self, action, _):
        builder = Gtk.Builder()
        builder.add_from_string(read_ui_file("about.glade"))
        builder.connect_signals(self)
        about_dialog = builder.get_object("about_dialog")
        about_dialog.props.modal = True
        about_dialog.set_transient_for(self.window)
        about_dialog.set_logo(self.window.get_icon())
        about_dialog.run()
        about_dialog.destroy()

    def help_cb(self, action, _):
        Gtk.show_uri(None, "help:plots", Gdk.CURRENT_TIME)

def read_ui_file(name):
    return importlib.resources.read_text("plots.ui", name)

if __name__ == '__main__':
    Plots().run(sys.argv)
