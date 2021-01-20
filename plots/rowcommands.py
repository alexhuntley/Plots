from plots import formularow, parser

class Delete():
    def __init__(self, row, rows):
        self.index = rows.index(row)
        self.formula = row.editor.expr.to_latex()
        self.adjustment = row.slider.get_adjustment()
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

class Add():
    def __init__(self, row, rows):
        self.index = rows.index(row)
        self.rgba = row.color_picker.get_rgba()

    def do(self, app):
        row = formularow.FormulaRow(app)
        app.insert_row(self.index, row)
        row.color_picker.set_rgba(self.rgba)

    def undo(self, app):
        app.rows[-1].delete(None, record=False)

class Edit():
    def __init__(self, row, rows, before):
        self.index = rows.index(row)
        self.before = before
        self.after = row.editor.expr.to_latex()

    def do(self, app):
        row = app.rows[self.index]
        row.editor.set_expr(parser.from_latex(self.after))
        row.editor.queue_draw()
        row.edited(None, record=False)

    def undo(self, app):
        row = app.rows[self.index]
        row.editor.set_expr(parser.from_latex(self.before))
        row.editor.queue_draw()
        row.edited(None, record=False)
