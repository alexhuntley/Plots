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

from enum import Enum
import re

import gi
from gi.repository import GLib, Gtk, Gdk, cairo, Pango, PangoCairo, GObject

desc = Pango.font_description_from_string("Latin Modern Math 20")

class Direction(Enum):
    UP = Gdk.KEY_Up
    DOWN = Gdk.KEY_Down
    LEFT = Gdk.KEY_Left
    RIGHT = Gdk.KEY_Right
    NONE = 0

    def displacement(self):
        if self is self.UP or self is self.LEFT:
            return -1
        elif self is self.DOWN or self is self.RIGHT:
            return 1
        else:
            return 0

    def end(self):
        return -1 if self.displacement() == -1 else 0

    def vertical(self):
        return self is self.UP or self is self.DOWN

    def horizontal(self):
        return not self.vertical()

class saved():
    """Context manager, ensures the cairo context is restored"""
    def __init__(self, ctx):
        self.ctx = ctx

    def __enter__(self):
        self.ctx.save()

    def __exit__(self ,exc_type, exc_val, exc_tb):
        self.ctx.restore()
        return False

class MetricContext():
    "Keeps track of state needed to calculate sizes"
    def __init__(self, cursor=None):
        self.prev = None
        self.paren_stack = []
        self.cursor = cursor


def italify_string(s):
    def italify_char(c):
        if c == 'h':
            return 'ℎ'
        # lowercase latin
        if c.islower() and ord(c) < 128:
            return chr(ord(c) - 0x61 + 0x1d44e)
        # uppercase latin
        if c.isupper() and ord(c) < 128:
            return chr(ord(c) - 0x41 + 0x1d434)
        # lowercase greek (n.b. don't italify uppers)
        if 0x3b1 <= ord(c) < 0x3b1 + 18:
            return chr(ord(c) - 0x3b1 + 0x1d6fc)
        return c
    return "".join(italify_char(c) for c in s)

def deitalify_char(c):
    if c == 'ℎ':
        return 'h'
    if 0x1d44e <= ord(c) < 0x1d44e + 26:
        return chr(ord(c) - 0x1d44e + 0x61)
    if 0x1d434 <= ord(c) < 0x1d434 + 26:
        return chr(ord(c) - 0x1d434 + 0x41)
    if 0x1d6fc <= ord(c) < 0x1d6fc + 18:
        return chr(ord(c) - 0x1d6fc + 0x3b1)
    return c

def deitalify_string(s):
    return "".join(deitalify_char(c) for c in s)


def ints_to_floats(string):
    return re.sub(r"(?<![\.\da-zA-Z_])(\d+)(?![\.\d])", r"\1.0", string)


class Text:
    def __init__(self, text, ctx, scale=1):
        self.scale = scale
        sf = scale/Pango.SCALE
        self.layout = PangoCairo.create_layout(ctx)
        self.layout.set_text(text, -1)
        self.layout.set_font_description(desc)
        self.width, self.height = self.layout.get_size()
        self.width *= sf
        self.height *= sf
        self.ascent = self.layout.get_baseline()*sf
        self.descent = self.height - self.ascent

        # Have to do this because get_pixel_extents returns integer pixels,
        # which are not precise enough
        self.ink_rect, self.logical_rect = self.layout.get_extents()
        for attr in ("x", "y", "width", "height"):
            setattr(self.ink_rect, attr, getattr(self.ink_rect, attr)*sf)
            setattr(self.logical_rect, attr, getattr(self.logical_rect, attr)*sf)

    def draw_at_baseline(self, ctx):
        with saved(ctx):
            ctx.move_to(0, -self.ascent)
            ctx.scale(self.scale, self.scale)
            PangoCairo.show_layout(ctx, self.layout)

    def draw(self, ctx):
        with saved(ctx):
            ctx.scale(self.scale, self.scale)
            self.update()
            PangoCairo.show_layout(ctx, self.layout)

    def update(self):
        self.layout.context_changed()

def font_metrics(ctx):
    return Text("x", ctx)

def rgba_to_tuple(rgba):
    return (rgba.red, rgba.green, rgba.blue, rgba.alpha)

def create_rgba(r, g, b, a=1.0):
    res = Gdk.RGBA()
    res.red = r
    res.green = g
    res.blue = b
    res.alpha = a
    return res
