import gi
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf

from plots import formula, plots, rowcommands
import re, math

class RowData():
    def __init__(self, type, expr=None, body=None, rgba=None, name=None):
        self.type = type
        if expr:
            self.expr = expr
        if body:
            self.body = body
        if rgba:
            self.rgba = rgba
        if name:
            self.name = name

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
        self.data = RowData("empty")
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
        m = re.match(r'^([a-zA-Z_]\w*) *=(.*)', expr)
        m2 = re.match(r'^([a-zA-Z_]\w*) *= *([+-]?([0-9]*[.])?[0-9]+)', expr)
        if m2 and m2.group(1) not in ["x", "y"]:
            self.data = RowData(type="slider", name=m2.group(1))
        elif m and m.group(1) not in ["x", "y"]:
            self.data = RowData(type="variable", body=body, expr=expr, name=m.group(1))
        elif m and m.group(1) == "y":
            self.data = RowData(type="formula", body=body, expr=m.group(2), rgba=rgba)
        elif expr:
            self.data = RowData(type="formula", body=body, expr=expr, rgba=rgba)
        else:
            self.data = RowData(type="empty")

        if self.data.type in ("variable", "slider"):
            self.color_picker.hide()
            self.name = m.group(1)
        else:
            self.color_picker.show()

        if self.data.type == "slider":
            self.slider_box.show()
            val = float(m2.group(2))
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

    def to_glsl(self):
        return self.data
