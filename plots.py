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

import numpy as np

class Plots:
    def __init__(self):
        self.scale = 1
        self.translation = np.array([0, 0], 'f')

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
        self.gl_area.connect("realize", self.gl_realize)

        for c in self.formula_box.get_children():
            self.formula_box.remove(c)

        self.formulae = [formula.Editor()]
        self.formula_box.pack_start(self.formulae[0], False, False, 0)

        self.window.set_default_size(600,400)
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

        VERTEX_SHADER = shaders.compileShader("""#version 330 core
        layout (location = 0) in vec3 position;
        out vec2 graph_pos;
        uniform vec2 viewport;
        uniform vec2 translation;
        uniform float scale;
        void main() {
            gl_Position = vec4(position, 1.0);
            vec2 normalised = position.xy * viewport / viewport.x;
            graph_pos = normalised*scale - translation;
        }""", GL_VERTEX_SHADER)

        FRAGMENT_SHADER = shaders.compileShader("""#version 330 core
        in vec2 graph_pos;
        out vec3 color;

        uniform vec2 pixel_extent;
        uniform float scale;

        float rand(vec2 co){
                // implementation found at: lumina.sourceforge.net/Tutorials/Noise.html
                return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
        }

        float y1(float x) {
            return sin(x*x);
            //return (x > 0. && x < 1.) ? 1. : 0.;
        }

        float y(float x) {
            float y = 0;
            for (float i = 1; i < 40; i+=2)
                y += sin(i*x)/i;
            return y;
        }

        void main() {
            vec2 samples = vec2(6, 6);
            vec2 step = 1.4*pixel_extent / samples;
            float jitter = 1.8;

            float count = 0;
            for (float i = 0.0; i < samples.x; i++) {
                for (float j = 0.0; j < samples.y; j++) {
                    float ii = i + jitter*rand(vec2(graph_pos.x+ i*step.x,graph_pos.y+ j*step.y));
                    float jj = j + jitter*rand(vec2(graph_pos.y + i*step.x,graph_pos.x+ j*step.y));
                    float f = y1(graph_pos.x + ii*step.x) - (graph_pos.y + jj*step.y);
                    count += (f > 0.) ? 1.0 : -1.0;
                }
            }
            float total_samples = samples.x*samples.y;
            color = vec3(1.0);
            if (abs(count) != total_samples) color = vec3(abs(count)/total_samples);
            float axis_width = pixel_extent.x;
            if (abs(graph_pos.x) < axis_width || abs(graph_pos.y) < axis_width) color -= 1.0-vec3(0.2,0.2,1.0);
            if (abs(mod(graph_pos.x, 1.0)) < axis_width || abs(mod(graph_pos.y, 1.0)) < axis_width) color -= 1.0-vec3(0.8, 0.8, 1.0);
        }""", GL_FRAGMENT_SHADER)

        self.shader = shaders.compileProgram(VERTEX_SHADER, FRAGMENT_SHADER)
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


if __name__ == '__main__':
    Plots().main()
