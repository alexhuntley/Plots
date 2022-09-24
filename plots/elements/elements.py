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
from gi.repository import GLib, Gtk, Gdk, cairo, Pango, PangoCairo, GObject
from plots.utils import saved, Direction, font_metrics, MetricContext, \
    deitalify_string, ints_to_floats
from plots.data import GREEK_REGEXES, FUNCTIONS, BINARY_OPERATORS, GREEK_LETTERS

DEBUG = False

from . import abstractelement

class ElementList(abstractelement.AbstractElement):
    h_spacing = 0

    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        if isinstance(elements, ElementList):
            self.elements = elements.elements
        else:
            self.elements = elements or []
        for i, e in enumerate(self.elements):
            e.parent = self
            e.index_in_parent = i

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    def __repr__(self):
        return "ElementList({!r})".format(self.elements)

    def __add__(self, other):
        return ElementList(self.elements + other.elements)

    def __getitem__(self, key):
        return self.elements[key]

    def children(self):
        return self.elements

    def compute_metrics(self, ctx, metric_ctx):
        self.ascent = self.descent = self.width = 0
        metric_ctx = MetricContext(metric_ctx.cursor)
        metric_ctx.prev = font_metrics(ctx)
        for i, e in enumerate(self.elements):
            e.index_in_parent = i
            e.compute_metrics(ctx, metric_ctx)
            self.ascent = max(self.ascent, e.ascent)
            self.descent = max(self.descent, e.descent)
            self.width += e.width + 2*e.h_spacing
            metric_ctx.prev = e
        if not self.elements:
            self.ascent = font_metrics(ctx).ascent
            self.descent = font_metrics(ctx).descent
            self.width = font_metrics(ctx).width

    def draw_cursor(self, ctx, ascent, descent, cursor, widget_transform):
        if cursor.owner is self and cursor.visible:
            #ctx.set_source_rgba(*element.Element.color)
            Gdk.cairo_set_source_rgba(ctx, element.Element.color)
            ctx.set_line_width(max(ctx.device_to_user_distance(cursor.WIDTH, cursor.WIDTH)))
            ctx.move_to(0, descent-2)
            ctx.line_to(0, -ascent+2)
            ctx.move_to(0, 0)
            ctx.stroke()
            cursor.position = widget_transform.transform_point(*ctx.user_to_device(0,0))

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        with saved(ctx):
            for i, e in enumerate(self.elements):
                ctx.move_to(0,0)
                if i == cursor.pos:
                    ascent, descent = e.ascent, e.descent
                    if cursor.pos > 0:
                        ascent = max(ascent, self.elements[i-1].ascent)
                        descent = max(descent, self.elements[i-1].descent)
                    self.draw_cursor(ctx, ascent, descent, cursor, widget_transform)
                ctx.move_to(0, 0)
                ctx.translate(e.h_spacing, 0)
                with saved(ctx):
                    e.draw(ctx, cursor, widget_transform)
                ctx.move_to(0,0)
                ctx.translate(e.width + e.h_spacing, 0)
            if cursor.pos == len(self.elements) > 0:
                self.draw_cursor(ctx, self.elements[-1].ascent, self.elements[-1].descent, cursor, widget_transform)
            elif not self.elements:
                self.draw_cursor(ctx, self.ascent, self.descent, cursor, widget_transform)
                ctx.set_source_rgba(0.5, 0.5, 0.5, 0.2)
                ctx.rectangle(0, -self.ascent, self.width, self.ascent + self.descent)
                ctx.fill()

    def backspace(self, cursor, caller=None, direction=Direction.LEFT):
        if self is not cursor.owner:
            cursor.reparent(self, direction.end())
        if direction is Direction.LEFT:
            shift = -1
        elif direction is Direction.RIGHT:
            shift = 0
        if cursor.pos + shift in range(len(self.elements)):
            target = self.elements[cursor.pos + shift]
            child = target.get_next_child(direction)
            if child is not None:
                cursor.reparent(child, direction.end())
                child.backspace(cursor, direction=direction)
            else:
                cursor.pos += shift
                del self.elements[cursor.pos]
        elif self.parent:
            self.parent.dissolve(cursor, self)

    def replace(self, old, new, cursor, cursor_offset=0):
        if old.parent is self:
            if isinstance(new, ElementList):
                self.elements[old.index_in_parent:old.index_in_parent+1] = new.elements
                for i, e in enumerate(new.elements):
                    e.parent = self
                    e.index_in_parent = old.index_in_parent + i
                if cursor_offset is not None:
                    cursor.reparent(self, old.index_in_parent + cursor_offset)
            else:
                self.elements[old.index_in_parent] = new
                new.parent = self

    def update_children(self):
        for i, e in enumerate(self.elements):
            e.parent = self
            e.index_in_parent = i

    def insert(self, element, cursor):
        self.elements.insert(cursor.pos, element)
        cursor.pos += 1
        self.update_children()
        self.convert_specials(cursor)
        if element.cursor_acceptor is not None:
            cursor.reparent(element.cursor_acceptor, -1)

    def insert_elementlist(self, new, cursor, position, cursor_right=True):
        self.elements[position:position] = new.elements
        self.update_children()
        if cursor_right:
            position += len(new)
        cursor.reparent(self, position)

    def greedy_insert(self, cls, cursor):
        eligible = (atom.Atom, radical.Radical)
        left, right = [], []
        if cursor.pos > 0 and cls.greedy_insert_left and \
           (isinstance(self.elements[cursor.pos-1], eligible) \
            or paren.Paren.is_paren(self.elements[cursor.pos-1], left=False)):
            paren_level = 0
            for n, e in enumerate(self.elements[cursor.pos-1::-1]):
                if paren.Paren.is_paren(e, left=True):
                    paren_level -= 1
                    if paren_level <= 0:
                        break
                elif paren.Paren.is_paren(e, left=False):
                    paren_level += 1
                if atom.Atom.part_of_number(e):
                    continue
                if paren_level <= 0:
                    n -= 1
                    break
            if paren_level >= 0:
                n = max(1, n + 1)
                left = self.elements[cursor.pos - n:cursor.pos]
                del self.elements[cursor.pos - n:cursor.pos]
                cursor.pos -= n
        if cursor.pos < len(self.elements) and cls.greedy_insert_right and \
           (isinstance(self.elements[cursor.pos], eligible) \
            or paren.Paren.is_paren(self.elements[cursor.pos], left=True)):
            paren_level = 0
            for n, e in enumerate(self.elements[cursor.pos:]):
                if paren.Paren.is_paren(e, left=False):
                    paren_level -= 1
                    if paren_level <= 0:
                        break
                elif paren.Paren.is_paren(e, left=True):
                    paren_level += 1
                if atom.Atom.part_of_number(e):
                    continue
                if paren_level <= 0:
                    n -= 1
                    break
            if paren_level >= 0:
                n = max(1, n + 1)
                right = self.elements[cursor.pos:cursor.pos + n]
                del self.elements[cursor.pos:cursor.pos + n]
        new = cls.make_greedily(left, right)
        self.insert(new, cursor)
        cursor.reparent(new.get_next_child(Direction.LEFT if left else Direction.RIGHT), 0)

    def atoms_at_cursor(self, cursor):
        l = cursor.pos
        while l - 1 >= 0:
            if isinstance(self.elements[l-1], (atom.Atom, atom.OperatorAtom)):
                l -= 1
            else:
                break
        r = cursor.pos
        while r < len(self.elements):
            if isinstance(self.elements[r], (atom.Atom, atom.OperatorAtom)):
                r += 1
            else:
                break
        return l, r

    @staticmethod
    def atoms_to_string(atoms):
        return "".join(deitalify_string(atom.name) for atom in atoms)

    def convert_specials(self, cursor):
        l, r = self.atoms_at_cursor(cursor)
        atoms = self.elements[l:r]
        names = index.string_to_names(self.atoms_to_string(atoms))

        # find index of first difference - it will be stored in i
        for i, name, atom in zip(count(), names, atoms):
            if name != deitalify_string(atom.name):
                break
        else:
            return

        new_elems = [index.name_to_element(name) for name in names]
        self.elements[l:r] = new_elems
        for j, elem in enumerate(new_elems):
            elem.parent = self
            elem.index_in_parent = l + j
        if new_elems[i].default_list:
            cursor.reparent(new_elems[i].default_list, 0)
        else:
            cursor.reparent(self, new_elems[i].index_in_parent)
            cursor.handle_movement(Direction.RIGHT)

    def to_glsl(self):
        string_stack = [[]]
        body_stack = [[]]
        sums = []
        sum_paren_levels = []
        prev = None
        parens = 0
        for elem in self.elements:
            if prev is not None and \
               not isinstance(prev, atom.BinaryOperatorAtom) and \
               not isinstance(elem, atom.BinaryOperatorAtom) and \
               not isinstance(elem, supersubscript.SuperscriptSubscript) and \
               not atom.Atom.part_of_number(elem) and \
               not paren.Paren.is_paren(elem, left=False) and \
               not paren.Paren.is_paren(prev, left=True) and \
               not isinstance(prev, atom.OperatorAtom) and \
               not isinstance(prev, sum.Sum) and \
               not (isinstance(elem, atom.Atom) and elem.name == "!"):
                string_stack[-1].append("*")
            # subscript log base
            if isinstance(elem, supersubscript.SuperscriptSubscript) \
               and elem.subscript is not None \
               and isinstance(prev, atom.OperatorAtom) \
               and prev.name == "log":
                assert string_stack[-1].pop() == "log"
                b, e = elem.subscript.to_glsl()
                body_stack[-1].append(b)
                string_stack[-1].append(f"log_base({e},")
                parens += 1
                prev = None
                continue
            if isinstance(prev, atom.OperatorAtom) and \
               not paren.Paren.is_paren(elem, left=True):
                string_stack[-1].append("(")
                parens += 1
            elif isinstance(elem, atom.BinaryOperatorAtom) or paren.Paren.is_paren(elem, left=False):
                string_stack[-1].append(")"*parens)
                parens = 0
            # Postscripts (exponents or factorials)
            if isinstance(elem, supersubscript.SuperscriptSubscript) and elem.exponent is not None \
               or isinstance(elem, atom.Atom) and elem.name == "!":
                parens2 = i = 0
                for i, s in reversed(list(enumerate(string_stack[-1]))):
                    if s == ")":
                        parens2 += 1
                    elif s == "(":
                        parens2 -= 1
                    if parens2 == 0 and s in "+-*=" or parens2 < 0:
                        i += 1
                        break
                if isinstance(elem, supersubscript.SuperscriptSubscript):
                    string_stack[-1].insert(i, "mypow(")
                    b, e = elem.exponent.to_glsl()
                    string_stack[-1].append(f", ({e}))")
                    body_stack[-1].append(b)
                else:
                    string_stack[-1].insert(i, "factorial(")
                    string_stack[-1].append(")")
            elif isinstance(elem, sum.Sum):
                string_stack.append([])
                body_stack.append([])
                sums.append(elem)
                sum_paren_levels.append(0)
            elif not isinstance(elem, supersubscript.SuperscriptSubscript):
                if (isinstance(elem, atom.BinaryOperatorAtom) or
                    paren.Paren.is_paren(elem, left=False)):
                    while sums and sum_paren_levels[-1] == 0:
                        sum_body, sum_expr = sums.pop().to_glsl("".join(body_stack.pop()),
                                                                "".join(string_stack.pop()))
                        sum_paren_levels.pop()
                        string_stack[-1].append(sum_expr)
                        body_stack[-1].append(sum_body)
                elem_body, elem_expr = elem.to_glsl()
                body_stack[-1].append(elem_body)
                string_stack[-1].append(elem_expr)
                if sums and paren.Paren.is_paren(elem, left=True):
                    sum_paren_levels[-1] += 1
                elif sums and paren.Paren.is_paren(elem, left=False):
                    sum_paren_levels[-1] -= 1
            prev = elem
        string_stack[-1].append(")"*parens)
        while sums:
            sum_body, sum_expr = sums.pop().to_glsl("".join(body_stack.pop()),
                                                    "".join(string_stack.pop()))
            sum_paren_levels.pop()
            string_stack[-1].append(sum_expr)
            body_stack[-1].append(sum_body)
        return ints_to_floats("".join(body_stack[-1])), \
            ints_to_floats("".join(string_stack[-1]))

    def to_latex(self):
        return "".join(e.to_latex() for e in self.elements)


from . import sum
from . import paren
from . import radical
from . import frac
from . import supersubscript
from . import atom
from . import index
from . import element
