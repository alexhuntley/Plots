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
from plots.elements import Element, ElementList, Text, BaseAtom, Atom, \
    BinaryOperatorAtom, OperatorAtom, SuperscriptSubscript, Frac, Radical, \
    Abs, Paren, Sum
from plots.utils import Direction, MetricContext
from plots.data import BINARY_OPERATORS

DEBUG = False

class Editor(Gtk.DrawingArea):
    padding = 4
    __gsignals__ = {
        'edit': (GObject.SIGNAL_RUN_LAST, None, ()),
        'cursor_position': (GObject.SIGNAL_RUN_FIRST, None, (float, float)),
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
        self.connect("key-press-event", self.on_key_press)
        self.connect('draw', self.do_draw_cb)
        self.connect("button-press-event", self.on_button_press)
        self.connect("realize", self.on_realise)
        self.connect("motion-notify-event", self.on_pointer_move)
        self.connect("focus-in-event", self.focus_in)
        self.connect("focus-out-event", self.focus_out)
        self.blink_source = None
        self.restart_blink_sequence()
        self.set_size_request(16, 20)

    def set_expr(self, new_expr):
        self.expr = new_expr
        self.cursor.reparent(self.expr, -1)
        self.cursor.cancel_selection()

    def do_draw_cb(self, widget, ctx):
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

    def on_key_press(self, widget, event):
        self.restart_blink_sequence()
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        if DEBUG:
            print(Gdk.keyval_name(event.keyval))
        if modifiers & (Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.MOD4_MASK):
            return False
        try:
            direction = Direction(event.keyval)
            select = bool(modifiers & Gdk.ModifierType.SHIFT_MASK)
            res = self.cursor.handle_movement(direction, select=select)
            self.queue_draw()
            return res
        except ValueError:
            pass

        char = chr(Gdk.keyval_to_unicode(event.keyval))
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
        if event.keyval == Gdk.KEY_BackSpace:
            self.cursor.backspace(Direction.LEFT)
            self.queue_draw()
            self.emit("edit")
            return
        if event.keyval == Gdk.KEY_Delete:
            self.cursor.backspace(Direction.RIGHT)
            self.queue_draw()
            self.emit("edit")
            return
        if event.keyval == Gdk.KEY_slash:
            self.cursor.greedy_insert(Frac)
            self.queue_draw()
            self.emit("edit")
            return
        if char == "^" or event.keyval == Gdk.KEY_dead_circumflex:
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
        element, direction = self.element_at(event.x, event.y)
        self.cursor.mouse_select(element, direction, drag=False)
        self.restart_blink_sequence()
        self.grab_focus()
        self.queue_draw()

    def on_pointer_move(self, widget, event):
        element, direction = self.element_at(event.x, event.y)
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

class Cursor():
    WIDTH = 1
    BLINK_DELAY = 600

    def __init__(self):
        self.owner = None
        self.visible = True
        self.pos = 0
        self.secondary_pos = None
        self.secondary_owner = None
        self.selecting = False
        self.selection_bounds = None
        self.selection_ancestor = None
        self.selection_rgba = [0.5, 0.5, 1, 0.6]
        self._position = (0., 0.)     # absolute position in widget (in pixels)
        self.position_changed = False  # set to True when self.position changes
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, new):
        if new != self._position:
            self._position = new
            self.position_changed = True

    @property
    def selection_slice(self):
        s = self.selection_bounds
        return slice(s.start, s.stop, s.step)

    def reparent(self, new_parent, position):
        self.owner = new_parent
        self.pos = position
        if position < 0:
            self.pos = len(self.owner.elements) + position + 1

    def cancel_selection(self):
        self.secondary_pos, self.secondary_owner = None, None
        self.selection_bounds, self.selection_ancestor = None, None
        self.selecting = False

    def select_all(self, root):
        self.reparent(root, -1)
        self.secondary_pos = 0
        self.secondary_owner = root
        self.selecting = True
        self.selection_bounds, self.selection_ancestor = self.calculate_selection()

    def copy_selection(self):
        elements = self.selection_ancestor.elements[self.selection_slice]
        text = "".join(e.to_latex() for e in elements)
        self.clipboard.set_text(text, -1)

    def cut_selection(self):
        self.copy_selection()
        self.backspace(None)

    def paste(self):
        text = self.clipboard.wait_for_text()
        elements = parser.from_latex(text)
        if self.selecting:
            self.backspace(None)
        self.owner.insert_elementlist(elements, self, self.pos)

    def mouse_select(self, element, direction, drag=False):
        if drag:
            if not self.selecting:
                self.secondary_pos = self.pos
                self.secondary_owner = self.owner
                self.selecting = True
        else:
            self.cancel_selection()
        if not isinstance(element, ElementList):
            pos = element.index_in_parent
            element = element.parent
            if direction is Direction.RIGHT:
                pos += 1
        else:
            if direction is Direction.LEFT:
                pos = 0
            else:
                pos = -1
        self.reparent(element, pos)
        if self.selecting:
            self.selection_bounds, self.selection_ancestor = self.calculate_selection()

    def handle_movement(self, direction, select=False):
        if select and not self.selecting:
            self.secondary_pos, self.secondary_owner = self.pos, self.owner
        elif not select:
            self.cancel_selection()
        self.selecting = select

        shift = 0 if direction.displacement() == 1 else -1

        def go_to_parent():
            if self.owner.parent:
                new_list = self.owner.parent.get_next_child(direction, self.owner)
                if new_list is not None:
                    self.owner = new_list
                    self.pos = len(self.owner) if direction.end() == -1 else 0
                else:
                    self.pos = self.owner.parent.index_in_parent + shift + 1
                    self.owner = self.owner.parent.parent
                return True
            return False

        if direction.vertical():
            return go_to_parent()
        adj_idx = self.pos + shift
        res = True
        try:
            if adj_idx < 0:
                raise IndexError
            adj = self.owner.elements[adj_idx]
            child_list = adj.get_next_child(direction)
            if child_list is not None:
                self.owner = child_list
                self.pos = len(self.owner) if direction.end() == -1 else 0
            else:
                new_pos = self.pos + direction.displacement()
                if new_pos in range(len(self.owner.elements) + 1):
                    self.pos = new_pos
                else:
                    res = False
        except IndexError:
            res = go_to_parent()
        if self.selecting:
            self.selection_bounds, self.selection_ancestor = self.calculate_selection()
        return res

    def calculate_selection(self):
        if not self.secondary_owner:
            return None
        primary_ancestors = self.ancestors(self.owner)
        secondary_ancestors = self.ancestors(self.secondary_owner)
        for i, l in enumerate(primary_ancestors):
            if l in secondary_ancestors:
                common_ancestor = l
                j = secondary_ancestors.index(l)
                break
        if i > 0:
            primary_ancestor_index = primary_ancestors[i-1].parent.index_in_parent
        else:
            primary_ancestor_index = self.pos
        if j > 0:
            secondary_ancestor_index = secondary_ancestors[j-1].parent.index_in_parent
        else:
            secondary_ancestor_index = self.secondary_pos
        if i > 0 and primary_ancestor_index >= secondary_ancestor_index:
            primary_ancestor_index += 1
        if j > 0 and secondary_ancestor_index >= primary_ancestor_index:
            secondary_ancestor_index += 1
        left = min(primary_ancestor_index, secondary_ancestor_index)
        right = max(primary_ancestor_index, secondary_ancestor_index)
        return range(left, right), common_ancestor

    @staticmethod
    def ancestors(elementlist):
        l = elementlist
        res = [l]
        while l.parent:
            l = l.parent.parent
            res.append(l)
        return res

    def backspace(self, direction):
        if self.selecting:
            sel = self.selection_ancestor.elements[self.selection_bounds.start:self.selection_bounds.stop]
            del self.selection_ancestor.elements[self.selection_bounds.start:self.selection_bounds.stop]
            self.reparent(self.selection_ancestor, self.selection_bounds.start)
            self.cancel_selection()
            return sel
        else:
            return self.owner.backspace(self, direction=direction)

    def insert(self, element, direction=Direction.LEFT):
        self.give_selected(element, direction=direction)
        self.owner.insert(element, self)

    def give_selected(self, element, direction=Direction.LEFT):
        if self.selecting:
            selection = self.backspace(None)
            element.accept_selection(selection, direction=direction)
            return len(selection)

    def greedy_insert(self, cls):
        if self.selecting:
            self.insert(cls())
        else:
            self.owner.greedy_insert(cls, self)

    def insert_superscript_subscript(self, superscript=True):
        new = False
        if self.pos > 0 and isinstance(self.owner.elements[self.pos - 1], SuperscriptSubscript):
            element = self.owner.elements[self.pos - 1]
            direction = Direction.RIGHT
        elif self.pos < len(self.owner) and \
             isinstance(self.owner.elements[self.pos], SuperscriptSubscript):
            element = self.owner.elements[self.pos]
            direction = Direction.LEFT
        elif self.secondary_owner is self.owner and self.secondary_pos > 0 and \
             isinstance(self.owner.elements[self.secondary_pos - 1], SuperscriptSubscript):
            element = self.owner.elements[self.secondary_pos - 1]
            direction = Direction.RIGHT
        elif self.secondary_owner is self.owner and self.secondary_pos < len(self.owner) and \
             isinstance(self.owner.elements[self.secondary_pos], SuperscriptSubscript):
            element = self.owner.elements[self.secondary_pos]
            direction = Direction.LEFT
        else:
            element  = SuperscriptSubscript()
            new = True
            direction = Direction.RIGHT
        if superscript:
            element.add_superscript(self)
        else:
            element.add_subscript(self)
        if new:
            self.insert(element, direction)
        else:
            selection_length = self.give_selected(element, direction)
            if direction is Direction.RIGHT:
                self.reparent(element.cursor_acceptor, -1)
            else:
                self.reparent(element.cursor_acceptor, selection_length or 0)
