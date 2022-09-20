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

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import OpenGL.GL as gl
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
from plots.data import jinja_env
from plots.i18n import _
import math
import numpy as np

from plots import utils
from plots.text import TextRenderer

class GraphArea(Gtk.GLArea):
    __gtype_name__ = "GraphArea"

    INIT_SCALE = 10
    ZOOM_BUTTON_FACTOR = 0.3

    def __init__(self):
        super().__init__()
        self.scale = self._target_scale = self.INIT_SCALE
        self._translation = np.array([0, 0], 'f')
        self.vertex_template = jinja_env.get_template('vertex.glsl')
        self.fragment_template = jinja_env.get_template('fragment.glsl')
        self.export_target = None
        self.connect("render", self.gl_render)
        self.connect("realize", self.gl_realize)
        self.app = None

        drag = Gtk.GestureDrag()
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("drag-update", self.drag_update)
        drag.connect("drag-begin", self.drag_begin)
        self.add_controller(drag)

        scroll_ctl = Gtk.EventControllerScroll()
        scroll_ctl.connect("scroll", self.scroll_zoom)
        scroll_ctl.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        self.add_controller(scroll_ctl)

        self.vertex_shader = None

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

    def do_css_changed(self, change):
        self.style_cb(self)
        self.queue_draw()

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

    def gl_realize(self, area):
        area.make_current()
        self.style_cb(area)

        if (area.get_error() is not None):
            return

        version = gl.glGetString(gl.GL_VERSION).decode().split(" ")[0]
        if version < "3.3":
            self.app.errorlabel.set_text(
                _("Warning: OpenGL {} is unsupported. Plots supports OpenGL 3.3 or greater.").format(version))
            self.app.errorbar.props.revealed = True

        self.vertex_shader = shaders.compileShader(
            self.vertex_template.render(), gl.GL_VERTEX_SHADER)
        self.app.update_shader()

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
        gl.glUniform1f(self.uniform("samples"), self.app.prefs["rendering"]["samples"])
        gl.glUniform1f(self.uniform("line_thickness"), self.app.prefs["rendering"]["line_thickness"])
        gl.glUniform3f(self.uniform("fg_color"), *self.fg_color)
        gl.glUniform3f(self.uniform("bg_color"), *self.bg_color)
        for slider in self.app.slider_rows:
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


    def style_cb(self, widget):
        ctx = self.get_style_context()
        self.fg_color = utils.rgba_to_tuple(ctx.lookup_color("window_fg_color").color)[:3]
        self.bg_color = utils.rgba_to_tuple(ctx.lookup_color("window_bg_color").color)[:3]

    def uniform(self, name):
        return gl.glGetUniformLocation(self.shader, name)

    def drag_update(self, gesture, dx, dy):
        dr = 2*np.array([dx, -dy], 'f')/self.viewport[0]*self.get_scale_factor()
        self.translation = self.init_translation + dr*self.scale
        self.queue_draw()

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
        self.queue_draw()

    def scroll_zoom(self, ctl, dx, dy):
        self.target_scale *= math.exp(dy*0.2)
        self.smooth_scroll()

    def zoom(self, button, factor):
        self.target_scale *= math.exp(factor*self.ZOOM_BUTTON_FACTOR)
        self.smooth_scroll()

    def reset_zoom(self, button):
        self.target_scale = self.INIT_SCALE
        self.smooth_scroll(translate_to=np.array([0, 0], 'f'))

    def update_zoom_reset(self):
        desired = self.target_scale != self.INIT_SCALE or self.translation.any()
        if self.app.zoom_reset_revealer.get_reveal_child() != desired:
            self.app.zoom_reset_revealer.set_reveal_child(desired)

    def update_fragment_shader(self, formulae):
        if self.vertex_shader:
            self.make_current()
            fragment_shader = shaders.compileShader(
                self.fragment_template.render(formulae=formulae),
                gl.GL_FRAGMENT_SHADER)
            self.shader = shaders.compileProgram(self.vertex_shader, fragment_shader)
            self.queue_draw()
