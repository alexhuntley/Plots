#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import formula
import converters
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from OpenGL.GL import shaders
from jinja2 import Environment, FileSystemLoader

import numpy as np

class Plots:
    def __init__(self):
        self.scale = 10
        self.translation = np.array([0, 0], 'f')
        self.jinja_env = Environment(loader=FileSystemLoader('./shaders'))
        self.vertex_template = self.jinja_env.get_template('vertex.glsl')
        self.fragment_template = self.jinja_env.get_template('fragment.glsl')
        self.formulae = []

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
        self.add_equation_button = builder.get_object("add_equation")

        self.gl_area = builder.get_object("gl")
        self.gl_area.connect("render", self.gl_render)
        self.gl_area.connect("realize", self.gl_realize)

        self.add_equation_button.connect("clicked", self.add_equation)

        for c in self.formula_box.get_children():
            self.formula_box.remove(c)

        self.add_equation(None)

        self.window.set_default_size(1200,800)
        self.window.show_all()

        self.drag = Gtk.GestureDrag(widget=self.gl_area)
        self.drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.drag.connect("drag-update", self.drag_update)
        self.drag.connect("drag-begin", self.drag_begin)
        self.gl_area.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.gl_area.connect('scroll_event', self.scroll_zoom)

        Gtk.main()

    def gl_render(self, area, context):
        area.make_current()
        w = area.get_allocated_width()
        h = area.get_allocated_height()
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
        dr = 2*np.array([dx, -dy], 'f')/self.viewport[0]
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

    def update_shader(self):
        exprs = []
        for f in self.formulae:
            body, expr = f.expr.to_glsl()
            if expr:
                exprs.append((body, expr))
        fragment_shader = shaders.compileShader(
            self.fragment_template.render(formulae=exprs),
            GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(self.vertex_shader, fragment_shader)


    def add_equation(self, _):
        builder = Gtk.Builder()
        builder.add_from_file("formula_box.glade")
        builder.connect_signals(self)
        formula_box = builder.get_object("formula_box")
        delete_button = builder.get_object("delete_button")
        editor = formula.Editor()

        editor.connect("edit", self.formula_edited)
        delete_button.connect("clicked", self.delete_equation, editor)
        formula_box.pack_start(editor, True, True, 0)
        formula_box.show_all()
        self.formula_box.pack_start(formula_box, False, False, 0)
        editor.grab_focus()
        self.formulae.append(editor)

    def delete_equation(self, widget, editor):
        self.formulae.remove(editor)
        widget.get_parent().destroy()

if __name__ == '__main__':
    Plots().main()
