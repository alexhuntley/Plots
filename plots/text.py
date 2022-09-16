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

import numpy as np
import freetype
import OpenGL.GL as gl
from OpenGL.GL import shaders
from OpenGL.arrays import vbo
import math
import glm
import importlib.resources as resources
from contextlib import contextmanager


# Code based on:
# - rougier/freetype-py
#   https://github.com/rougier/freetype-py/blob/master/examples/opengl.py
# - LearnOpenGL Text Rendering
#   https://learnopengl.com/In-Practice/Text-Rendering
class TextRenderer():
    def __init__(self, fontsize=14, scale_factor=1):
        self.base, self.texid = 0, 0
        self.width, self.height = 0, 0
        self.characters = []
        self.initgl()
        self.fontsize = fontsize * scale_factor
        self.makefont(resources.open_binary('plots.res', 'DejaVuSans.ttf'),
                      self.fontsize)

    def initgl(self):
        vert = resources.read_text("plots.shaders", "text_vert.glsl")
        frag = resources.read_text("plots.shaders", "text_frag.glsl")
        vert = shaders.compileShader(vert, gl.GL_VERTEX_SHADER)
        frag = shaders.compileShader(frag, gl.GL_FRAGMENT_SHADER)
        self.shaderProgram = shaders.compileProgram(vert, frag)
        self.vbo = vbo.VBO(np.array([
            # x y  u  v
            0, -1, 0, 0,
            0,  0, 0, 1,
            1,  0, 1, 1,
            0, -1, 0, 0,
            1,  0, 1, 1,
            1, -1, 1, 0
        ], 'f'), usage="GL_STATIC_DRAW")
        self.vao = gl.glGenVertexArrays(1)

        gl.glBindVertexArray(self.vao)
        self.vbo.bind()
        self.vbo.copy_data()
        gl.glVertexAttribPointer(0, 4, gl.GL_FLOAT, False, 4*self.vbo.data.itemsize, self.vbo)
        gl.glEnableVertexAttribArray(0)
        self.vbo.unbind()
        gl.glBindVertexArray(0)

    def makefont(self, filename, fontsize):
        face = freetype.Face(filename)
        face.set_pixel_sizes(0, fontsize)

        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glActiveTexture(gl.GL_TEXTURE0)

        self.top_bearing = 0
        for c in range(128):
            face.load_char(chr(c), freetype.FT_LOAD_RENDER)
            glyph = face.glyph
            bitmap = glyph.bitmap
            size = bitmap.width, bitmap.rows
            bearing = glyph.bitmap_left, glyph.bitmap_top
            self.top_bearing = max(self.top_bearing, bearing[1])
            advance = glyph.advance.x

            # create glyph texture
            texObj = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texObj)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_R8, *size, 0, gl.GL_RED, gl.GL_UNSIGNED_BYTE, bitmap.buffer)

            self.characters.append((texObj, size, bearing, advance))

        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def uniform(self, name):
        return gl.glGetUniformLocation(self.shaderProgram, name)

    @contextmanager
    def render(self, width, height):
        self.width, self.height = width, height
        gl.glUseProgram(self.shaderProgram)
        proj = glm.ortho(0, self.width, self.height, 0, -1, 1)
        gl.glUniformMatrix4fv(self.uniform("projection"),
                           1, gl.GL_FALSE, glm.value_ptr(proj))
        yield self

    def width_of(self, text, scale=1):
        return sum((self.characters[ord(c)][3] >> 6)*scale for c in text)

    def render_text(self, text, pos, scale=1, dir=(1,0), halign='left',
                    valign='bottom', text_color=(.0, .0, .0), bg_color=(1., 1., 1.)):
        offset = glm.vec3()
        if halign in ('center', 'right'):
            width = self.width_of(text, scale)
            offset.x -= width
            if halign == 'center':
                offset.x /= 2
        if valign in ('center', 'top'):
            offset.y += self.top_bearing
            if valign == 'center':
                offset.y /= 2
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindVertexArray(self.vao)
        angle_rad = math.atan2(dir[1], dir[0])
        rotateM = glm.rotate(glm.mat4(1), angle_rad, glm.vec3(0, 0, 1))
        transOriginM = glm.translate(glm.mat4(1), glm.vec3(*pos, 0) + offset)
        gl.glUniform3f(self.uniform("fg_color"), *text_color)
        gl.glUniform3f(self.uniform("bg_color"), *bg_color)
        char_x = 0
        for c in text:
            c = ord(c)
            ch = self.characters[c]
            w, h = ch[1][0] * scale, ch[1][1] * scale
            xrel, yrel = char_x + ch[2][0] * scale, (ch[1][1] - ch[2][1]) * scale
            char_x += (ch[3] >> 6) * scale
            scaleM = glm.scale(glm.mat4(1), glm.vec3(w, h, 1))
            transRelM = glm.translate(glm.mat4(1), glm.vec3(xrel, yrel, 0))
            modelM = transOriginM * rotateM * transRelM * scaleM

            gl.glUniformMatrix4fv(self.uniform("model"),
                               1, gl.GL_FALSE, glm.value_ptr(modelM))
            gl.glBindTexture(gl.GL_TEXTURE_2D, ch[0])
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)

        gl.glBindVertexArray(0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
