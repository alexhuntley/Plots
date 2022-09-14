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

import re
from itertools import count

import gi
gi.require_version('PangoCairo', '1.0')
from gi.repository import GLib, Gtk, Gdk, cairo, Pango, PangoCairo, GObject
from enum import Enum
from plots import parser
from plots.elements import Element, ElementList, BaseAtom, Atom, \
    BinaryOperatorAtom, OperatorAtom, SuperscriptSubscript, Frac, Radical, \
    Abs, Paren, Sum
from plots.utils import Direction, MetricContext, Text
from plots.data import BINARY_OPERATORS
from plots.cursor import Cursor

DEBUG = False

class Editor(Gtk.DrawingArea):
    padding = 4
    __gsignals__ = {
        'edit': (GObject.SignalFlags.RUN_LAST, None, ()),
        'cursor_position': (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
    }
    def __init__(self, expression=None):
        super().__init__()
        self.cursor = Cursor()
        if expression:
            self.expr = expression
        else:
            self.expr = ElementList()
        self.cursor.reparent(self.expr, -1)
        self.props.can_focus = True
        self.key_ctl = Gtk.EventControllerKey()
        self.key_ctl.connect("key-pressed", self.on_key_press)
        self.add_controller(self.key_ctl)
        #self.connect('draw', self.do_draw_cb)
        self.set_draw_func(self.do_draw_cb)
        #self.connect("button-press-event", self.on_button_press)
        self.connect("realize", self.on_realise)
        self.motion_ctl = Gtk.EventControllerMotion()
        self.motion_ctl.connect("motion", self.on_pointer_move)
        self.add_controller(self.motion_ctl)
        #self.connect("focus-in-event", self.focus_in)
        #self.connect("focus-out-event", self.focus_out)
        self.blink_source = None
        self.restart_blink_sequence()
        self.set_size_request(16, 20)

    def set_expr(self, new_expr):
        self.expr = new_expr
        self.cursor.reparent(self.expr, -1)
        self.cursor.cancel_selection()

    def do_draw_cb(self, widget, ctx, w, h):
        Element.color = self.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        widget_transform = ctx.get_matrix()
        widget_transform.invert()
        ctx.translate(self.padding, self.padding) # a bit of padding
        scale = 1
        ctx.scale(scale, scale)
        self.expr.compute_metrics(ctx, MetricContext(self.cursor))
        ctx.translate(0, self.expr.ascent)
        self.set_size_request(self.expr.width*scale + 2*self.padding,
                              (self.expr.ascent + self.expr.descent)*scale + 2*self.padding)
        self.expr.draw(ctx, self.cursor, widget_transform)
        if self.cursor.position_changed:
            self.emit("cursor_position", *self.cursor.position)
            self.cursor.position_changed = False

    def focus_in(self, widget, event):
        self.restart_blink_sequence()

    def focus_out(self, widget, event):
        GLib.source_remove(self.blink_source)
        self.blink_source = None
        self.cursor.cancel_selection()
        self.cursor.visible = False
        self.queue_draw()

    def blink_cursor_cb(self):
        self.cursor.visible = not self.cursor.visible
        self.queue_draw()
        return True

    def restart_blink_sequence(self):
        if not self.cursor.visible:
            self.cursor.visible = True
        if self.blink_source:
            GLib.source_remove(self.blink_source)
        self.blink_source = GLib.timeout_add(Cursor.BLINK_DELAY, self.blink_cursor_cb)

    def on_key_press(self, event_cont, keyval, keycode, state):
        self.restart_blink_sequence()
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        if DEBUG:
            print(Gdk.keyval_name(keyval))
        if modifiers & (Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.MOD4_MASK):
            return False
        try:
            direction = Direction(keyval)
            select = bool(modifiers & Gdk.ModifierType.SHIFT_MASK)
            res = self.cursor.handle_movement(direction, select=select)
            self.queue_draw()
            return res
        except ValueError:
            pass

        char = chr(Gdk.keyval_to_unicode(keyval))
        if modifiers & Gdk.ModifierType.CONTROL_MASK:
            if char == "a":
                self.cursor.select_all(self.expr)
                self.queue_draw()
                return True
            elif char == "c":
                self.cursor.copy_selection()
                self.queue_draw()
                return True
            elif char == "x":
                self.cursor.cut_selection()
                self.queue_draw()
                self.emit("edit")
                return True
            elif char == "v":
                self.cursor.paste()
                self.queue_draw()
                self.emit("edit")
                return True
            else:
                return False
        if char in "⁰¹²³⁴⁵⁶⁷⁸⁹":
            self.cursor.insert_superscript_subscript(superscript=True)
            translation = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
            self.cursor.insert(Atom(char.translate(translation)))
            self.cursor.handle_movement(Direction(Gdk.KEY_Right), select=False) # reset cursor level
            self.queue_draw()
            self.emit("edit")
            return
        if char.isalnum():
            self.cursor.insert(Atom(char))
            self.queue_draw()
            self.emit("edit")
            return
        if char in BINARY_OPERATORS:
            translation = str.maketrans("-*", "−×")
            self.cursor.insert(BinaryOperatorAtom(char.translate(translation)))
            self.queue_draw()
            self.emit("edit")
            return
        if char in "!'.":
            translation = str.maketrans("'", "′")
            self.cursor.insert(Atom(char.translate(translation)))
            self.queue_draw()
            self.emit("edit")
            return
        if char in "()[]{}":
            self.cursor.insert(Paren(char))
            self.queue_draw()
            self.emit("edit")
            return
        if keyval == Gdk.KEY_BackSpace:
            self.cursor.backspace(Direction.LEFT)
            self.queue_draw()
            self.emit("edit")
            return
        if keyval == Gdk.KEY_Delete:
            self.cursor.backspace(Direction.RIGHT)
            self.queue_draw()
            self.emit("edit")
            return
        if keyval in (Gdk.KEY_slash, Gdk.KEY_KP_Divide):
            self.cursor.greedy_insert(Frac)
            self.queue_draw()
            self.emit("edit")
            return
        if char == "^" or keyval == Gdk.KEY_dead_circumflex:
            self.cursor.insert_superscript_subscript(superscript=True)
            self.queue_draw()
            self.emit("edit")
            return
        if char == "_":
            self.cursor.insert_superscript_subscript(superscript=False)
            self.queue_draw()
            self.emit("edit")
            return
        if char == "|":
            self.cursor.insert(Abs(None))
            self.queue_draw()
            self.emit("edit")
            return

        self.queue_draw()

    def element_at(self, x, y):
        e = self.expr
        while True:
            for c in e.children():
                if c.contains_device_point(x, y):
                    e = c
                    break
            else:
                return e, e.half_containing(x, y)

    def on_button_press(self, widget, event):
        if event.button == 1:
            if event.type is Gdk.EventType.DOUBLE_BUTTON_PRESS or \
               event.type is Gdk.EventType.TRIPLE_BUTTON_PRESS:
                self.cursor.select_all(self.expr)
            else:
                element, direction = self.element_at(event.x, event.y)
                self.cursor.mouse_select(element, direction, drag=False)
                self.restart_blink_sequence()
                self.grab_focus()
            self.queue_draw()
            return True

    def on_pointer_move(self, ctl, x, y):
        element, direction = self.element_at(x, y)
        self.cursor.mouse_select(element, direction, drag=True)
        self.restart_blink_sequence()
        self.queue_draw()

    def on_realise(self, widget):
        w = self.get_window()
        w.set_events(w.get_events() | \
                     Gdk.EventMask.KEY_PRESS_MASK | \
                     Gdk.EventMask.BUTTON_PRESS_MASK | \
                     Gdk.EventMask.BUTTON_MOTION_MASK)
        w.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "text"))
