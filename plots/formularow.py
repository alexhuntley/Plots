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

import gi
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, Adw

from plots import formula, plots, rowcommands, colorpicker, utils
from plots.data import jinja_env
import re, math
from enum import Enum

class RowData():
    def id(self):
        return id(self)


class Empty(RowData):
    priority = 0
    def __init__(self, owner, **kwargs):
        self.owner = owner
        self.rgba = None

    def definition(self):
        return ""

    def calculation(self):
        return ""

    @staticmethod
    def accepts(expr):
        return True


class Variable(RowData):
    priority = 50
    def __init__(self, owner, body, expr, rgba=None):
        self.owner = owner
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
    priority = 80
    def __init__(self, owner, body, expr, rgba):
        self.owner = owner
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
    priority = 20
    calculation_template = jinja_env.get_template("formula_calculation.glsl")

    def __init__(self, owner, expr, body, rgba):
        self.owner = owner
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
    priority = 20
    calculation_template = jinja_env.get_template("x_formula_calculation.glsl")

    def __init__(self, owner, expr, body, rgba):
        self.owner = owner
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
    priority = 20
    calculation_template = jinja_env.get_template("r_formula_calculation.glsl")

    def __init__(self, owner, expr, body, rgba):
        self.owner = owner
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
    priority = 20
    calculation_template = jinja_env.get_template("theta_formula_calculation.glsl")

    def __init__(self, owner, expr, body, rgba):
        self.owner = owner
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


class ImplicitFormula(RowData):
    priority = 20
    calculation_template = jinja_env.get_template("implicit_formula_calculation.glsl")

    def __init__(self, owner, expr, body, rgba):
        self.owner = owner
        m = re.match(r'^([^=]+)=([^=]+)$', expr)
        self.body = body
        self.rgba = rgba
        self.expr = "{} - {}".format(m.group(1), m.group(2));

    @staticmethod
    def accepts(expr):
        m = re.match(r'^([^=]+)=([^=]+)$', expr)
        return bool(m)

    def definition(self):
        return f"""float formula{self.id()}(float x, float y) {{
    {self.body}
    return {self.expr};
}}"""

    def calculation(self):
        return self.calculation_template.render(formula=self)


class RowStatus(Enum):
    GOOD = 1
    BAD = 2
    UNKNOWN = 3


@Gtk.Template(string=utils.read_ui_file("formula_box.glade"))
class FormulaBox(Gtk.Box):
    __gtype_name__ = "FormulaBox"

    BLACK = [0,0,0]
    WHITE = [238, 238, 236]
    PALETTE = [
        BLACK,
        [28,113,216],
        [46,194,126],
        [245,194,17],
        [230,97,0  ],
        [192,28,40 ],
        [129,61,156],
        [134,94,60 ],
    ]
    DARK_PALETTE = [WHITE] + PALETTE[1:]
    PALETTE = [utils.create_rgba(*(color/255 for color in colors)) for colors in PALETTE]
    DARK_PALETTE = [utils.create_rgba(*(color/255 for color in colors)) for colors in DARK_PALETTE]
    _palette_use_next = 0

    delete_button = Gtk.Template.Child()
    viewport = Gtk.Template.Child("editor_viewport")
    button_box = Gtk.Template.Child()
    slider = Gtk.Template.Child()
    slider_upper = Gtk.Template.Child()
    slider_lower = Gtk.Template.Child()
    slider_box = Gtk.Template.Child()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.data = Empty(self)

        self.color_picker = colorpicker.PopoverColorPicker()
        self.button_box.append(self.color_picker)
        self.color_picker.add_palette(Gtk.Orientation.HORIZONTAL, 9, FormulaBox.PALETTE)
        self.color_picker.set_rgba(FormulaBox.PALETTE[FormulaBox._palette_use_next])
        FormulaBox._palette_use_next = (FormulaBox._palette_use_next + 1) % len(FormulaBox.PALETTE)
        self.editor = formula.Editor()
        self.editor.connect("edit", self.edited)
        self.editor.connect("cursor_position", self.cursor_position)
        self.delete_button.connect("clicked", self.delete)
        self.color_picker.connect("color-activated", self.on_color_activated)
        self.slider.connect("value-changed", self.slider_changed)
        self.slider_upper.connect("changed", self.slider_limits_changed)
        self.slider_lower.connect("changed", self.slider_limits_changed)
        self.viewport.set_child(self.editor)
        self.connect("realize", self.on_realize)
        self.editor.grab_focus()
        self.old = self.construct_memory()
        self.use_dark_style = False
        self.row_status = RowStatus.UNKNOWN

    def on_realize(self, widget):
        self.slider_box.hide()

    def delete(self, widget, record=True, replace_if_last=True):
        if record:
            self.app.add_to_history(rowcommands.Delete(self, self.app.rows))
        self.app.rows.remove(self)
        self.app.formula_box.remove(self)
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

    def on_color_activated(self, widget, chooser, color):
        self.edited(widget)

    def edited(self, widget, record=True):
        body, expr = self.editor.expr.to_glsl()
        rgba = utils.rgba_to_tuple(self.color_picker.get_rgba())

        for cls in [Formula, XFormula, RFormula, ThetaFormula,
                    Slider, Variable, ImplicitFormula, Empty]:
            if cls.accepts(expr):
                self.data = cls(self, body=body, expr=expr, rgba=rgba)
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
        self.row_status = RowStatus.UNKNOWN
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

    def do_css_changed(self, change):
        style = self.style_is_dark()
        if style != self.use_dark_style:
            self.use_dark_style = style
            new_palette = [self.PALETTE, self.DARK_PALETTE][self.use_dark_style]
            old_palette = [self.PALETTE, self.DARK_PALETTE][not self.use_dark_style]
            new_color = old_color = self.color_picker.get_rgba()
            if old_color.equal(old_palette[0]):
                new_color = new_palette[0]
            self.color_picker.add_palette(Gtk.Orientation.HORIZONTAL, 9, None)
            self.color_picker.add_palette(Gtk.Orientation.HORIZONTAL, 9, new_palette)
            self.color_picker.set_rgba(new_color)
            self.edited(None, record=False)

    def style_is_dark(self):
        return Adw.StyleManager.get_default().get_dark()
