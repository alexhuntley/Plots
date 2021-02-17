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
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

from plots import formula, formularow, rowcommands
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
from jinja2 import Environment, FileSystemLoader, PackageLoader
import sys
try:
    import importlib.resources as resources
except ModuleNotFoundError:
    import importlib_resources as resources
import re
import math
import numpy as np

class Plots(Gtk.Application):
    INIT_SCALE = 10
    def __init__(self):
        super().__init__(application_id="com.github.alexhuntley.Plots")
        self._scale = self.INIT_SCALE
        self._translation = np.array([0, 0], 'f')
        self.jinja_env = Environment(loader=PackageLoader('plots', 'shaders'))
        self.vertex_template = self.jinja_env.get_template('vertex.glsl')
        self.fragment_template = self.jinja_env.get_template('fragment.glsl')
        self.rows = []
        self.slider_rows = []
        self.history = []
        self.history_position = 0 # index of the last undone command / next in line for redo
        self.overlay_source = None

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self.update_zoom_reset()

    @property
    def translation(self):
        return self._translation

    @translation.setter
    def translation(self, value):
        self._translation = value
        self.update_zoom_reset()

    def key_pressed(self, widget, event):
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        char = chr(Gdk.keyval_to_unicode(event.keyval))
        if event.keyval == Gdk.KEY_Return:
            self.add_equation(None)
            return True
        elif modifiers & Gdk.ModifierType.CONTROL_MASK:
            if char == "z":
                self.undo(None)
                return True
            elif char == "y" or char == "Z" and modifiers & Gdk.ModifierType.SHIFT_MASK:
                self.redo(None)
                return True

    def do_activate(self):
        builder = Gtk.Builder()
        builder.add_from_string(read_ui_file("plots.glade"))
        builder.connect_signals(self)

        self.window = builder.get_object("main_window")
        self.add_window(self.window)
        loader = GdkPixbuf.PixbufLoader()
        loader.write(resources.read_binary("plots.res", "com.github.alexhuntley.Plotter.svg"))
        loader.close()
        self.window.set_icon(loader.get_pixbuf())
        self.window.set_title("Plots")
        self.scroll = builder.get_object("equation_scroll")
        self.formula_box = builder.get_object("equation_box")
        self.add_equation_button = builder.get_object("add_equation")
        self.undo_button = builder.get_object("undo")
        self.redo_button = builder.get_object("redo")
        self.window.connect("key-press-event", self.key_pressed)

        self.gl_area = builder.get_object("gl")
        self.gl_area.connect("render", self.gl_render)
        self.gl_area.connect("realize", self.gl_realize)

        self.errorbar = builder.get_object("errorbar")
        self.errorbar.set_message_type(Gtk.MessageType.ERROR)
        self.errorbar.connect("response", lambda id, data: self.errorbar.set_property("revealed", False))
        self.errorlabel = builder.get_object("errorlabel")

        self.add_equation_button.connect("clicked", self.add_equation)
        self.undo_button.connect("clicked", self.undo)
        self.redo_button.connect("clicked", self.redo)

        self.osd_revealer = builder.get_object("osd_revealer")
        self.zoom_reset_revealer = builder.get_object("zoom_reset_revealer")
        self.graph_overlay = builder.get_object("graph_overlay")
        self.zoom_in_button = builder.get_object("zoom_in")
        self.zoom_in_button.connect("clicked", self.zoom, -0.1)
        self.zoom_out_button = builder.get_object("zoom_out")
        self.zoom_out_button.connect("clicked", self.zoom, 0.1)
        self.zoom_reset_button = builder.get_object("zoom_reset")
        self.zoom_reset_button.connect("clicked", self.reset_zoom)
        self.update_zoom_reset()

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

        self.set_overlay_timeout()

        self.add_equation(None, record=False)

        self.window.set_default_size(1280, 720)
        self.window.show_all()

        css = '''
.formula_box {
        background-color: @theme_base_color;
        border-bottom-color: @borders;
        border-bottom-width: 1px;
        border-bottom-style: solid;
}
.zoom-box {
        background-color: rgba(0, 0, 0, 0);
}
'''
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css.encode())
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider,
                                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.drag = Gtk.GestureDrag(widget=self.gl_area)
        self.drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.drag.connect("drag-update", self.drag_update)
        self.drag.connect("drag-begin", self.drag_begin)
        self.gl_area.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.gl_area.connect('scroll_event', self.scroll_zoom)
        self.gl_area.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.gl_area.connect('motion-notify-event', self.motion_cb)
        self.graph_overlay.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        self.graph_overlay.connect('enter-notify-event', self.enter_overlay_cb)

        self.refresh_history_buttons()

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
        for slider in self.slider_rows:
            glUniform1f(glGetUniformLocation(self.shader, slider.name), slider.value)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, 18)
        glBindVertexArray(0)

        return True

    def gl_realize(self, area):
        area.make_current()

        if (area.get_error() != None):
            return

        version = glGetString(GL_VERSION).decode().split(" ")[0]
        if version < "3.3":
            self.errorlabel.set_text(f"Warning: OpenGL {version} is unsupported. Plots supports OpenGL 3.3 or greater.")
            self.errorbar.props.revealed = True

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
        self.scale *= math.exp(dy/10)
        widget.queue_draw()

    def zoom(self, button, factor):
        self.scale *= math.exp(factor)
        self.gl_area.queue_draw()

    def reset_zoom(self, button):
        self.scale = self.INIT_SCALE
        self.translation = np.array([0, 0], 'f')
        self.gl_area.queue_draw()

    def clear_overlay_timeout(self):
        if self.overlay_source is not None:
            GLib.source_remove(self.overlay_source)
            self.overlay_source = None

    def set_overlay_timeout(self):
        self.clear_overlay_timeout()
        self.overlay_source = GLib.timeout_add(2000, self.overlay_timeout_cb)

    def overlay_timeout_cb(self):
        self.osd_revealer.set_reveal_child(False)
        self.overlay_source = None

    def motion_cb(self, widget, event):
        if not self.osd_revealer.get_reveal_child():
            self.osd_revealer.set_reveal_child(True)
        self.set_overlay_timeout()
        return False

    def enter_overlay_cb(self, widget, event):
        self.clear_overlay_timeout()
        return False

    def update_zoom_reset(self):
        desired = self.scale != self.INIT_SCALE or self.translation.any()
        if self.zoom_reset_revealer.get_reveal_child() != desired:
            self.zoom_reset_revealer.set_reveal_child(desired)


    def update_shader(self):
        formulae = []
        variables = []
        sliders = []
        self.slider_rows.clear()
        for r in self.rows:
            data = r.to_glsl()
            if data.type == "formula":
                formulae.append(data)
            elif data.type == "variable":
                variables.append(data)
            elif data.type == "slider":
                sliders.append(data)
                self.slider_rows.append(r)
        try:
            fragment_shader = shaders.compileShader(
                self.fragment_template.render(formulae=formulae, variables=variables,
                                              sliders=sliders),
                GL_FRAGMENT_SHADER)
        except RuntimeError as e:
            print(e.args[0].encode('ascii', 'ignore').decode('unicode_escape'))
            fragment_shader = shaders.compileShader(
                self.fragment_template.render(formulae=[], variables=[], sliders=[]),
                GL_FRAGMENT_SHADER)
            #print(e.args[1][0].decode())
        self.shader = shaders.compileProgram(self.vertex_shader, fragment_shader)
        self.gl_area.queue_draw()

    def add_equation(self, _, record=True):
        row = formularow.FormulaRow(self)
        self.rows.append(row)
        self.formula_box.pack_start(row.formula_box, False, False, 0)
        row.editor.grab_focus()
        if record:
            self.add_to_history(rowcommands.Add(row, self.rows))

    def insert_row(self, index, row):
        self.rows.insert(index, row)
        self.formula_box.pack_start(row.formula_box, False, False, 0)
        self.formula_box.reorder_child(row.formula_box, index)
        row.editor.grab_focus()

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

    def add_to_history(self, command):
        if self.can_redo():
            del self.history[self.history_position:]
        self.history.append(command)
        self.history_position = len(self.history)
        self.refresh_history_buttons()

    def can_undo(self):
        return self.history_position > 0

    def can_redo(self):
        return self.history_position < len(self.history)

    def undo(self, _):
        if self.can_undo():
            self.history_position -= 1
            self.history[self.history_position].undo(self)
            self.refresh_history_buttons()

    def redo(self, _):
        if self.history_position < len(self.history):
            self.history[self.history_position].do(self)
            self.history_position += 1
            self.refresh_history_buttons()

    def refresh_history_buttons(self):
        self.undo_button.props.sensitive = self.can_undo()
        self.redo_button.props.sensitive = self.can_redo()

def read_ui_file(name):
    return resources.read_text("plots.ui", name)

if __name__ == '__main__':
    Plots().run(sys.argv)
