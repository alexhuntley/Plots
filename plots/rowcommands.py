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

from plots import formularow, parser
from collections import namedtuple

RowMemory = namedtuple("RowMemory", "formula rgba lower upper slider")

class Delete():
    def __init__(self, row, rows):
        self.index = rows.index(row)
        self.formula = row.editor.expr.to_latex()
        self.rgba = row.color_picker.get_rgba()
        self.last = len(rows) == 1

    def do(self, app):
        app.rows[self.index].delete(None, record=False)

    def undo(self, app):
        if self.last:
            app.rows[0].delete(None, record=False, replace_if_last=False)
        row = formularow.FormulaRow(app)
        app.insert_row(self.index, row)
        row.editor.set_expr(parser.from_latex(self.formula))
        row.color_picker.set_rgba(self.rgba)
        row.edited(None, record=False)
        row.grab_focus()

class Add():
    def __init__(self, row, rows):
        self.index = rows.index(row)
        self.rgba = row.color_picker.get_rgba()

    def do(self, app):
        row = formularow.FormulaRow(app)
        app.insert_row(self.index, row)
        row.color_picker.set_rgba(self.rgba)
        row.editor.grab_focus()

    def undo(self, app):
        app.rows[-1].delete(None, record=False)

class Edit():
    def __init__(self, row, rows, new, old):
        self.index = rows.index(row)
        self.before = old
        self.after = new

    def do(self, app):
        row = app.rows[self.index]
        row.editor.set_expr(parser.from_latex(self.after.formula))
        row.color_picker.set_rgba(self.after.rgba)
        row.editor.grab_focus()
        row.editor.queue_draw()
        row.edited(None, record=False)

    def undo(self, app):
        row = app.rows[self.index]
        row.editor.set_expr(parser.from_latex(self.before.formula))
        row.color_picker.set_rgba(self.before.rgba)
        row.editor.grab_focus()
        row.editor.queue_draw()
        row.edited(None, record=False)
