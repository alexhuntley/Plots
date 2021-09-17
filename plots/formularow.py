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

import gi
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf

from plots import formula, plots, rowcommands
from plots.data import jinja_env
import re, math

class RowData():
    def id(self):
        return id(self)


class Empty(RowData):
    def __init__(self, **kwargs):
        self.rgba = None

    def definition(self):
        return ""

    def calculation(self):
        return ""

    @staticmethod
    def accepts(expr):
        return True


class Variable(RowData):
    def __init__(self, body, expr, rgba=None):
        m = re.match(r'^([a-zA-Z_]\w*) *=(.*)', expr)
        self.name = m.group(1)
        self.body = body
        self.expr = expr

    def definition(self):
        return f"float {self.name} = 0.0;\n"

    def calculation(self):
        return f"{self.body}\n{self.expr};\n"

    @staticmethod
    def accepts(expr):
        m = re.match(r'^([a-zA-Z_]\w*) *=(.*)', expr)
        return m and m.group(1) not in ["x", "y"]


class Slider(RowData):
    def __init__(self, body, expr, rgba):
        m = re.match(r'^([a-zA-Z_]\w*) *= *([+-]?([0-9]*[.])?[0-9]+)', expr)
        self.name = m.group(1)
        self.value = float(m.group(2))

    def definition(self):
        return f"uniform float {self.name};\n"

    def calculation(self):
        return ""

    @staticmethod
    def accepts(expr):
        m = re.match(r'^([a-zA-Z_]\w*) *= *([+-]?([0-9]*[.])?[0-9]+)', expr)
        return m and m.group(1) not in ["x", "y"]


class Formula(RowData):
    calculation_template = jinja_env.get_template("formula_calculation.glsl")

    def __init__(self, expr, body, rgba):
        m = re.match(r'^(?:y *=)?(.+)', expr)
        self.expr = m.group(1)
        self.body = body
        self.rgba = rgba

    def definition(self):
        return f"""float formula{self.id()}(float x) {{
    {self.body}
    return {self.expr};
}}"""

    def calculation(self):
        return self.calculation_template.render(formula=self)

    @staticmethod
    def accepts(expr):
        m = re.match(r'^(?:y *=)?(.+)', expr)
        return m and "=" not in m.group(1)


class XFormula(RowData):
    calculation_template = jinja_env.get_template("x_formula_calculation.glsl")

    def __init__(self, expr, body, rgba):
        m = re.match(r'^x *=(.+)', expr)
        self.expr = m.group(1)
        self.body = body
        self.rgba = rgba

    def definition(self):
        return f"""float formula{self.id()}(float y) {{
    {self.body}
    return {self.expr};
}}"""

    def calculation(self):
        return self.calculation_template.render(formula=self)

    @staticmethod
    def accepts(expr):
        m = re.match(r'^x *=(.+)', expr)
        return bool(m)


class RFormula(RowData):
    calculation_template = jinja_env.get_template("r_formula_calculation.glsl")

    def __init__(self, expr, body, rgba):
        m = re.match(r'^r *=(.+)', expr)
        self.expr = m.group(1)
        self.body = body
        self.rgba = rgba

    def definition(self):
        return f"""float formula{self.id()}(float theta) {{
    {self.body}
    return {self.expr};
}}"""

    def calculation(self):
        return self.calculation_template.render(formula=self)

    @staticmethod
    def accepts(expr):
        m = re.match(r'^r *=(.+)', expr)
        return bool(m)


class ThetaFormula(RowData):
    calculation_template = jinja_env.get_template("theta_formula_calculation.glsl")

    def __init__(self, expr, body, rgba):
        m = re.match(r'^theta *=(.+)', expr)
        self.expr = m.group(1)
        self.body = body
        self.rgba = rgba

    def definition(self):
        return f"""float formula{self.id()}(float r) {{
    {self.body}
    return {self.expr};
}}"""

    def calculation(self):
        return self.calculation_template.render(formula=self)

    @staticmethod
    def accepts(expr):
        m = re.match(r'^theta *=(.+)', expr)
        return bool(m)


class FormulaRow():
    PALETTE = [
        [0,0,0     ],
        [28,113,216],
        [46,194,126],
        [245,194,17],
        [230,97,0  ],
        [192,28,40 ],
        [129,61,156],
        [134,94,60 ],
    ]
    PALETTE = [Gdk.RGBA(*(color/255 for color in colors)) for colors in PALETTE]
    _palette_use_next = 0

    def __init__(self, app):
        self.app = app
        self.data = Empty()
        builder = Gtk.Builder()
        builder.add_from_string(plots.read_ui_file("formula_box.glade"))
        builder.connect_signals(self)
        self.formula_box = builder.get_object("formula_box")
        self.delete_button = builder.get_object("delete_button")
        self.viewport = builder.get_object("editor_viewport")
        self.color_picker = builder.get_object("color_button")
        self.slider_box = builder.get_object("slider_box")
        self.slider = builder.get_object("slider")
        self.slider_upper = builder.get_object("slider_upper")
        self.slider_lower = builder.get_object("slider_lower")
        self.color_picker.add_palette(Gtk.Orientation.HORIZONTAL, 9, FormulaRow.PALETTE)
        self.color_picker.set_rgba(FormulaRow.PALETTE[FormulaRow._palette_use_next])
        FormulaRow._palette_use_next = (FormulaRow._palette_use_next + 1) % len(FormulaRow.PALETTE)
        self.editor = formula.Editor()
        self.editor.connect("edit", self.edited)
        self.editor.connect("cursor_position", self.cursor_position)
        self.delete_button.connect("clicked", self.delete)
        self.color_picker.connect("color-set", self.edited)
        self.slider.connect("value-changed", self.slider_changed)
        self.slider_upper.connect("changed", self.slider_limits_changed)
        self.slider_lower.connect("changed", self.slider_limits_changed)
        self.viewport.add(self.editor)
        self.formula_box.show_all()
        self.formula_box.connect("realize", self.on_realize)
        self.editor.grab_focus()
        self.old = self.construct_memory()

    def on_realize(self, widget):
        self.slider_box.hide()
        self.slider.set_adjustment(Gtk.Adjustment(0.5, 0, 1, 0.1, 0, 0))

    def delete(self, widget, record=True, replace_if_last=True):
        if record:
            self.app.add_to_history(rowcommands.Delete(self, self.app.rows))
        self.app.rows.remove(self)
        self.formula_box.destroy()
        if not self.app.rows and replace_if_last:
            self.app.add_equation(None, record=False)
        self.app.update_shader()

    def cursor_position(self, widget, x, y):
        adj = widget.get_parent().get_hadjustment().props
        # Force adjustment to update to new size
        adj.upper = max(widget.get_size_request()[0], adj.page_size)
        if x - 4 < adj.value:
            adj.value = x - 4
        elif x + 4 > adj.value + adj.page_size:
            adj.value = x - adj.page_size + 4

    def edited(self, widget, record=True):
        body, expr = self.editor.expr.to_glsl()
        rgba = tuple(self.color_picker.get_rgba())

        for cls in [Formula, XFormula, RFormula, ThetaFormula, Slider, Variable, Empty]:
            if cls.accepts(expr):
                self.data = cls(body=body, expr=expr, rgba=rgba)
                break

        if hasattr(self.data, 'rgba'):
            self.color_picker.show()
        else:
            self.color_picker.hide()
            self.name = self.data.name

        if isinstance(self.data, Slider):
            self.slider_box.show()
            val = self.data.value
            if val == 0:
                u, l = 10., -10.
            else:
                u = 10**(1+math.floor(math.log10(abs(val))))
                l = -abs(u)/10
                if val < 0:
                    u, l = -l, -u
                u = max(u, 10.0)
                l = min(l, -10.0)
            self.slider_upper.set_text(str(u))
            self.slider_lower.set_text(str(l))
            self.slider.set_value(val)
        else:
            self.slider_box.hide()

        mem = self.construct_memory()
        if record:
            command = rowcommands.Edit(self, self.app.rows, mem, self.old)
            self.app.add_to_history(command)
        self.old = mem
        self.app.update_shader()

    def construct_memory(self):
        adj = self.slider.get_adjustment()
        return rowcommands.RowMemory(
            formula=self.editor.expr.to_latex(),
            rgba=self.color_picker.get_rgba(),
            lower=adj.get_lower(),
            upper=adj.get_upper(),
            slider=adj.get_value())

    def slider_changed(self, widget):
        self.editor.cursor.cancel_selection()
        equals_index = self.editor.expr.elements.index(formula.BinaryOperatorAtom("="))
        del self.editor.expr.elements[equals_index+1:]
        cursor = self.editor.cursor
        cursor.reparent(self.editor.expr, -1)
        new_val = round(self.slider.get_value(), 4)
        for char in str(int(new_val) if new_val.is_integer() else new_val):
            if char == "-":
                self.editor.expr.insert(formula.BinaryOperatorAtom("−"), cursor)
            elif char.isdigit() or char == ".":
                self.editor.expr.insert(formula.Atom(char), cursor)
        self.editor.queue_draw()
        self.app.gl_area.queue_draw()

    def slider_limits_changed(self, widget):
        try:
            if widget is self.slider_upper:
                self.slider.get_adjustment().set_upper(float(widget.get_text()))
            elif widget is self.slider_lower:
                self.slider.get_adjustment().set_lower(float(widget.get_text()))
        except ValueError:
            pass

    @property
    def value(self):
        return self.slider.get_value()

    def get_data(self):
        return self.data
