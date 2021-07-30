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

import numpy as np
import freetype
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GL import shaders
from OpenGL.arrays import vbo
import math
import glm
try:
    import importlib.resources as resources
except ModuleNotFoundError:
    import importlib_resources as resources
from contextlib import contextmanager


# Code based on:
# - rougier/freetype-py
#   https://github.com/rougier/freetype-py/blob/master/examples/opengl.py
# - LearnOpenGL Text Rendering
#   https://learnopengl.com/In-Practice/Text-Rendering
class TextRenderer():
    def __init__(self):
        self.base, self.texid = 0, 0
        self.width, self.height = 0, 0
        self.characters = []
        self.initgl()
        self.fontsize = 14
        self.makefont(resources.open_binary('plots.res', 'DejaVuSans.ttf'),
                      self.fontsize)

    def initgl(self):
        vert = resources.read_text("plots.shaders", "text_vert.glsl")
        frag = resources.read_text("plots.shaders", "text_frag.glsl")
        vert = shaders.compileShader(vert, GL_VERTEX_SHADER)
        frag = shaders.compileShader(frag, GL_FRAGMENT_SHADER)
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
        self.vao = glGenVertexArrays(1)

        glBindVertexArray(self.vao)
        self.vbo.bind()
        self.vbo.copy_data()
        glVertexAttribPointer(0, 4, GL_FLOAT, False, 4*self.vbo.data.itemsize, self.vbo)
        glEnableVertexAttribArray(0)
        self.vbo.unbind()
        glBindVertexArray(0)

    def makefont(self, filename, fontsize):
        face = freetype.Face(filename)
        face.set_pixel_sizes(0, fontsize)

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glActiveTexture(GL_TEXTURE0)

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
            texObj = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texObj)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_R8, *size, 0, GL_RED, GL_UNSIGNED_BYTE, bitmap.buffer)

            self.characters.append((texObj, size, bearing, advance))

        glPixelStorei(GL_UNPACK_ALIGNMENT, 4)
        glBindTexture(GL_TEXTURE_2D, 0)

    def uniform(self, name):
        return glGetUniformLocation(self.shaderProgram, name)

    @contextmanager
    def render(self, width, height):
        self.width, self.height = width, height
        glUseProgram(self.shaderProgram)
        proj = glm.ortho(0, self.width, self.height, 0, -1, 1)
        glUniformMatrix4fv(self.uniform("projection"),
                           1, GL_FALSE, glm.value_ptr(proj))
        yield self

    def width_of(self, text, scale=1):
        return sum((self.characters[ord(c)][3] >> 6)*scale for c in text)

    def render_text(self, text, pos, scale=1, dir=(1,0), halign='left', valign='bottom'):
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
        glActiveTexture(GL_TEXTURE0)
        glBindVertexArray(self.vao)
        angle_rad = math.atan2(dir[1], dir[0])
        rotateM = glm.rotate(glm.mat4(1), angle_rad, glm.vec3(0, 0, 1))
        transOriginM = glm.translate(glm.mat4(1), glm.vec3(*pos, 0) + offset)
        glUniform3f(self.uniform("textColor"), .0, .0, .0)
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

            glUniformMatrix4fv(self.uniform("model"),
                               1, GL_FALSE, glm.value_ptr(modelM))
            glBindTexture(GL_TEXTURE_2D, ch[0])
            glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
