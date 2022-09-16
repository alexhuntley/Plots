#!/usr/bin/env python3

# Copyright 2021-2022 Alexander Huntley

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
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf, cairo, Adw

from plots import formula, formularow, rowcommands, preferences, utils
from plots.text import TextRenderer
from plots.i18n import _
from plots.data import jinja_env
import plots.i18n
import OpenGL.GL as gl
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
import sys
import importlib.resources as resources
import re
import math
import numpy as np

class Plots(Adw.Application):
    INIT_SCALE = 10
    ZOOM_BUTTON_FACTOR = 0.3

    def __init__(self):
        super().__init__(application_id="com.github.alexhuntley.Plots")
        self.scale = self._target_scale = self.INIT_SCALE
        self._translation = np.array([0, 0], 'f')
        self.vertex_template = jinja_env.get_template('vertex.glsl')
        self.fragment_template = jinja_env.get_template('fragment.glsl')
        self.rows = []
        self.slider_rows = []
        self.history = []
        self.history_position = 0  # index of the last undone command / next in line for redo
        self.overlay_source = None
        self.export_target = None
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.PREFER_LIGHT)
        plots.i18n.bind()

    @property
    def target_scale(self):
        return self._target_scale

    @target_scale.setter
    def target_scale(self, value):
        self._target_scale = value
        self.update_zoom_reset()

    @property
    def translation(self):
        return self._translation

    @translation.setter
    def translation(self, value):
        self._translation = value
        self.update_zoom_reset()

    def key_pressed(self, ctl, keyval, keycode, state):
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        char = chr(Gdk.keyval_to_unicode(keyval))
        if keyval == Gdk.KEY_Return:
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
        builder.set_translation_domain(plots.i18n.domain)

        self.window = builder.get_object("main_window")
        self.add_window(self.window)
        loader = GdkPixbuf.PixbufLoader()
        loader.write(resources.read_binary("plots.res", "com.github.alexhuntley.Plotter.svg"))
        loader.close()
        #self.window.set_icon(loader.get_pixbuf())
        self.window.set_title("Plots")
        self.scroll = builder.get_object("equation_scroll")
        self.formula_box = builder.get_object("equation_box")
        self.add_equation_button = builder.get_object("add_equation")
        self.undo_button = builder.get_object("undo")
        self.redo_button = builder.get_object("redo")
        self.key_ctl = Gtk.EventControllerKey()
        self.key_ctl.connect("key-pressed", self.key_pressed)
        self.window.add_controller(self.key_ctl)
        self.window.connect("close-request", self.delete_cb)

        self.gl_area = builder.get_object("gl")
        self.gl_area.connect("render", self.gl_render)
        self.gl_area.connect("realize", self.gl_realize)

        self.errorbar = builder.get_object("errorbar")
        self.errorbar.set_message_type(Gtk.MessageType.ERROR)
        self.errorbar.connect("response", lambda id, data: self.errorbar.set_property("revealed", False))
        self.errorbar.props.revealed = False
        self.errorlabel = builder.get_object("errorlabel")

        self.add_equation_button.connect("clicked", self.add_equation)
        self.undo_button.connect("clicked", self.undo)
        self.redo_button.connect("clicked", self.redo)

        self.osd_revealer = builder.get_object("osd_revealer")
        self.zoom_reset_revealer = builder.get_object("zoom_reset_revealer")
        self.graph_overlay = builder.get_object("graph_overlay")
        self.zoom_in_button = builder.get_object("zoom_in")
        self.zoom_in_button.connect("clicked", self.zoom, -self.ZOOM_BUTTON_FACTOR)
        self.zoom_out_button = builder.get_object("zoom_out")
        self.zoom_out_button.connect("clicked", self.zoom, self.ZOOM_BUTTON_FACTOR)
        self.zoom_reset_button = builder.get_object("zoom_reset")
        self.zoom_reset_button.connect("clicked", self.reset_zoom)
        self.update_zoom_reset()

        menu_button = builder.get_object("menu_button")

        self.menu = Gio.Menu()
        self.menu.append(_("_Export…"), "app.export")
        self.menu.append(_("_Preferences"), "app.preferences")
        self.menu.append(_("Help"), "app.help")
        self.menu.append(_("About Plots"), "app.about")
        menu_button.set_menu_model(self.menu)

        self.about_action = Gio.SimpleAction.new("about", None)
        self.about_action.connect("activate", self.about_cb)
        self.about_action.set_enabled(True)
        self.add_action(self.about_action)

        about_builder = Gtk.Builder()
        about_builder.add_from_string(read_ui_file("about.glade"))
        self.about_dialog = about_builder.get_object("about_dialog")
        self.about_dialog.props.modal = True
        self.about_dialog.set_transient_for(self.window)
        self.about_dialog.set_modal(True)

        help_action = Gio.SimpleAction.new("help", None)
        help_action.connect("activate", self.help_cb)
        help_action.set_enabled(True)
        self.add_action(help_action)

        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", self.export_cb)
        export_action.set_enabled(True)
        self.add_action(export_action)

        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self.prefs_cb)
        prefs_action.set_enabled(True)
        self.add_action(prefs_action)
        self.prefs = preferences.Preferences(self.window)

        #for c in self.formula_box.get_children():
        #    self.formula_box.remove(c)

        self.set_overlay_timeout()

        self.add_equation(None, record=False)

        self.window.set_default_size(1280, 720)

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
        context = self.window.get_style_context()
        display = self.window.get_display()
        context.add_provider_for_display(display, css_provider,
                                         Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.drag = Gtk.GestureDrag()
        self.drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.drag.connect("drag-update", self.drag_update)
        self.drag.connect("drag-begin", self.drag_begin)
        self.gl_area.add_controller(self.drag)
        scroll_ctl = Gtk.EventControllerScroll()
        scroll_ctl.connect("scroll", self.scroll_zoom)
        scroll_ctl.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        self.gl_area.add_controller(scroll_ctl)
        motion_ctl = Gtk.EventControllerMotion()
        motion_ctl.connect("motion", self.motion_cb)
        self.gl_area.add_controller(motion_ctl)
        overlay_motion_ctl = Gtk.EventControllerMotion()
        overlay_motion_ctl.connect("enter", self.enter_overlay_cb)
        self.graph_overlay.add_controller(overlay_motion_ctl)
        self.refresh_history_buttons()
        self.window.show()

    @staticmethod
    def major_grid(pixel_extent):
        min_extent = 100*pixel_extent
        exponent = math.floor(math.log10(abs(min_extent)))
        mantissa = min_extent/10**exponent
        major = 1.0
        for m in (2.0, 5.0, 10.0):
            if m > mantissa:
                major = m * 10**exponent
                minor = major / (4 if m == 2 else 5)
                return major, minor

    def graph_to_device(self, graph_pos):
        normalised = (graph_pos + self.translation)/self.scale
        gl_pos = normalised / self.viewport * self.viewport[0]
        gl_pos[1] *= -1
        return (gl_pos/2 + 0.5) * self.viewport

    def device_to_graph(self, pixel):
        gl_pos = 2*(pixel/self.viewport - 0.5)
        gl_pos[1] *= -1
        normalised = gl_pos * self.viewport / self.viewport[0]
        return normalised*self.scale - self.translation

    def gl_render(self, area, context):
        area.make_current()
        w = area.get_allocated_width() * area.get_scale_factor()
        h = area.get_allocated_height() * area.get_scale_factor()
        self.viewport = np.array([w, h], 'f')
        self.render()

        if self.export_target:
            width, height = self.viewport.astype(int)
            pixels = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                pixels, GdkPixbuf.Colorspace.RGB, False, 8,
                width, height, width*3, None, None
            ).flip(horizontal=False)
            pixbuf.savev(self.export_target, "png", [])
            self.export_target = None
        return True

    def style_cb(self, widget):
        ctx = self.window.get_style_context()
        self.fg_color = utils.rgba_to_tuple(ctx.lookup_color("window_fg_color").color)[:3]
        self.bg_color = utils.rgba_to_tuple(ctx.lookup_color("window_bg_color").color)[:3]

    def render(self):
        graph_extent = 2*self.viewport/self.viewport[0]*self.scale
        # extent of each pixel, in graph coordinates
        pixel_extent = graph_extent / self.viewport
        w, h = self.viewport.astype(int)

        gl.glViewport(0, 0, w, h)

        gl.glClearColor(0, 0, 1, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        major_grid, minor_grid = self.major_grid(pixel_extent[0])
        shaders.glUseProgram(self.shader)
        gl.glUniform2f(self.uniform("viewport"), *self.viewport)
        gl.glUniform2f(self.uniform("translation"), *self.translation)
        gl.glUniform2f(self.uniform("pixel_extent"), *pixel_extent)
        gl.glUniform1f(self.uniform("scale"), self.scale)
        gl.glUniform1f(self.uniform("major_grid"), major_grid)
        gl.glUniform1f(self.uniform("minor_grid"), minor_grid)
        gl.glUniform1f(self.uniform("samples"), self.prefs["rendering"]["samples"])
        gl.glUniform1f(self.uniform("line_thickness"), self.prefs["rendering"]["line_thickness"])
        gl.glUniform3f(self.uniform("fg_color"), *self.fg_color)
        gl.glUniform3f(self.uniform("bg_color"), *self.bg_color)
        for slider in self.slider_rows:
            gl.glUniform1f(self.uniform(slider.name), slider.value)
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 18)
        gl.glBindVertexArray(0)

        with self.text_renderer.render(w, h) as r:
            low = major_grid * np.floor(
                self.device_to_graph(np.array([0, h]))/major_grid)
            high = major_grid * np.ceil(
                self.device_to_graph(np.array([w, 0]))/major_grid)
            n = (high - low)/major_grid
            pad = 4
            for i in range(round(n[0])+1):
                x = low[0] + i*major_grid
                pos = self.graph_to_device(np.array([x, 0]))
                pos[1] = np.clip(pos[1] + pad, pad, self.viewport[1] - r.top_bearing - pad)
                if x:
                    r.render_text("%g" % x, pos, valign='top', halign='center',
                                  text_color=self.fg_color, bg_color=self.bg_color)
            for j in range(round(n[1])+1):
                y = low[1] + j*major_grid
                label = "%g" % y
                pos = self.graph_to_device(np.array([0, y]))
                pos[0] = np.clip(pos[0] - pad, r.width_of(label) + pad, self.viewport[0] - pad)
                if y:
                    r.render_text(label, pos, valign='center', halign='right',
                                  text_color=self.fg_color, bg_color=self.bg_color)
            r.render_text("0", self.graph_to_device(np.zeros(2)) + np.array([-pad, pad]),
                          valign='top', halign='right', text_color=self.fg_color, bg_color=self.bg_color)


    def uniform(self, name):
        return gl.glGetUniformLocation(self.shader, name)

    def gl_realize(self, area):
        area.make_current()
        #area.connect("style-updated", self.style_cb)
        self.style_cb(area)

        if (area.get_error() is not None):
            return

        version = gl.glGetString(gl.GL_VERSION).decode().split(" ")[0]
        if version < "3.3":
            self.errorlabel.set_text(
                _("Warning: OpenGL {} is unsupported. Plots supports OpenGL 3.3 or greater.").format(version))
            self.errorbar.props.revealed = True

        self.vertex_shader = shaders.compileShader(
            self.vertex_template.render(), gl.GL_VERTEX_SHADER)
        self.update_shader()

        self.vbo = vbo.VBO(np.array([
            [-1, -1, 0],
            [-1, 1, 0],
            [1, 1, 0],
            [-1, -1, 0],
            [1, -1, 0],
            [1, 1, 0]
        ], 'f'), usage="GL_STATIC_DRAW_ARB")

        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)
        self.vbo.bind()
        self.vbo.copy_data()
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 3*self.vbo.data.itemsize, self.vbo)
        gl.glEnableVertexAttribArray(0)
        self.vbo.unbind()
        gl.glBindVertexArray(0)

        self.text_renderer = TextRenderer(scale_factor=area.get_scale_factor())

    def drag_update(self, gesture, dx, dy):
        dr = 2*np.array([dx, -dy], 'f')/self.viewport[0]*self.gl_area.get_scale_factor()
        self.translation = self.init_translation + dr*self.scale
        self.gl_area.queue_draw()

    def drag_begin(self, gesture, start_x, start_y):
        self.init_translation = self.translation

    def smooth_scroll(self, translate_to=None):
        speed = 0.3
        self.scale = speed*self.target_scale + (1-speed)*self.scale
        if translate_to is not None:
            self.translation = speed*translate_to + (1-speed)*self.translation
        if abs(self.scale/self.target_scale - 1) > 0.01 or \
           (translate_to is not None and
                (np.abs(self.translation - translate_to) > 0.01).any()):
            GLib.timeout_add(1000/60, self.smooth_scroll, translate_to)
        else:
            self.scale = self.target_scale
            if translate_to is not None:
                self.translation = translate_to
        self.gl_area.queue_draw()

    def scroll_zoom(self, ctl, dx, dy):
        self.target_scale *= math.exp(dy*0.2)
        self.smooth_scroll()

    def zoom(self, button, factor):
        self.target_scale *= math.exp(factor)
        self.smooth_scroll()

    def reset_zoom(self, button):
        self.target_scale = self.INIT_SCALE
        self.smooth_scroll(translate_to=np.array([0, 0], 'f'))

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

    def motion_cb(self, ctl, x, y):
        if not self.osd_revealer.get_reveal_child():
            self.osd_revealer.set_reveal_child(True)
        self.set_overlay_timeout()
        return False

    def enter_overlay_cb(self, ctl, x, y):
        self.clear_overlay_timeout()
        return False

    def update_zoom_reset(self):
        desired = self.target_scale != self.INIT_SCALE or self.translation.any()
        if self.zoom_reset_revealer.get_reveal_child() != desired:
            self.zoom_reset_revealer.set_reveal_child(desired)

    def update_shader(self):
        formulae = []
        self.slider_rows.clear()
        for r in self.rows:
            if r.row_status == formularow.RowStatus.BAD:
                continue
            data = r.get_data()
            formulae.append(data)
            if isinstance(data, formularow.Slider):
                self.slider_rows.append(r)
        formulae.sort(key=lambda x: x.priority, reverse=True)
        try:
            fragment_shader = shaders.compileShader(
                self.fragment_template.render(formulae=formulae),
                gl.GL_FRAGMENT_SHADER)
            for f in formulae:
                if f.owner.row_status == formularow.RowStatus.UNKNOWN:
                    f.owner.row_status = formularow.RowStatus.GOOD
        except RuntimeError as e:
            print(e.args[0].encode('ascii', 'ignore').decode('unicode_escape'))
            good_formulae = [f for f in formulae
                             if f.owner.row_status == formularow.RowStatus.GOOD]
            fragment_shader = shaders.compileShader(
                self.fragment_template.render(formulae=good_formulae),
                gl.GL_FRAGMENT_SHADER)
            for f in formulae:
                if f.owner.row_status == formularow.RowStatus.UNKNOWN:
                    f.owner.row_status = formularow.RowStatus.BAD
        self.shader = shaders.compileProgram(self.vertex_shader, fragment_shader)
        self.gl_area.queue_draw()

    def add_equation(self, _, record=True):
        row = formularow.FormulaBox(self)
        self.rows.append(row)
        self.formula_box.append(row)
        row.editor.grab_focus()
        if record:
            self.add_to_history(rowcommands.Add(row, self.rows))

    def insert_row(self, index, row):
        self.rows.insert(index, row)
        prev = self.rows[index-1] if index > 0 else None
        self.formula_box.insert_child_after(row, prev)
        row.editor.grab_focus()

    def about_cb(self, action, _):
        #about_dialog.set_logo(self.window.get_icon())
        self.about_dialog.show()

    def prefs_cb(self, action, param):
        self.prefs.show()

    def help_cb(self, action, _):
        Gtk.show_uri(None, "help:plots", Gdk.CURRENT_TIME)

    def export_cb(self, action, parameter):
        self.export_dialog = Gtk.FileChooserNative.new(
            title=_("Export image"),
            parent=self.window,
            action=Gtk.FileChooserAction.SAVE,
            accept_label=_("_Export"),
            cancel_label=_("_Cancel")
        )
        self.export_dialog.set_current_name(_("Untitled plot") + ".png")
        self.export_dialog.connect("response", self.export_response)
        self.export_dialog.set_modal(True)
        self.export_dialog.show()

    def export_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            self.export_target = dialog.get_file().get_path()
            self.gl_area.queue_draw()
        elif response == Gtk.ResponseType.CANCEL:
            pass
        dialog.destroy()
        self.export_dialog = None

    def delete_cb(self, window):
        self.prefs.save_config()

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
