from . import elements
from . import element
from plots.utils import saved, Direction

class SuperscriptSubscript(element.Element):
    h_spacing = 0
    exponent_scale = 0.7
    subscript_scale = 0.7
    subscript_shift = 6
    superscript_adjustment = 14

    def __init__(self, parent=None, exponent=None, subscript=None):
        super().__init__(parent)
        self.exponent = exponent
        self.subscript = subscript
        self.lists = []
        self._selection_acceptor = None
        self.update_lists()

    def __repr__(self):
        return f"SuperscriptSubscript(exponent={repr(self.exponent)}, subscript={repr(self.subscript)})"

    def add_superscript(self, cursor):
        if self.exponent is None:
            self.exponent = elements.ElementList([], self)
            self.update_lists()
        self.cursor_acceptor = self.exponent
        self._selection_acceptor = self.exponent

    def add_subscript(self, cursor):
        if self.subscript is None:
            self.subscript = elements.ElementList([], self)
            self.update_lists()
        self.cursor_acceptor = self.subscript
        self._selection_acceptor = self.subscript

    def update_lists(self):
        self.lists = [x for x in (self.exponent, self.subscript) if x is not None]
        for l in self.lists:
            l.parent = self

    def compute_metrics(self, ctx, metric_ctx):
        self.width = 0
        self.ascent = max(0, metric_ctx.prev.ascent)
        self.descent = max(0, metric_ctx.prev.descent)
        if self.exponent is not None:
            self.exponent.compute_metrics(ctx, metric_ctx)
            self.superscript_shift = -self.exponent.descent*self.exponent_scale \
                - metric_ctx.prev.ascent + self.superscript_adjustment # -ve y is up
            self.width = max(self.width, self.exponent.width*self.exponent_scale)
            self.ascent = max(self.ascent, self.exponent.ascent*self.exponent_scale - self.superscript_shift)
            self.descent = max(self.descent, self.exponent.descent*self.exponent_scale + self.superscript_shift)
        if self.subscript is not None:
            self.subscript.compute_metrics(ctx, metric_ctx)
            self.width = max(self.width, self.subscript.width*self.subscript_scale)
            self.ascent = max(self.ascent, self.subscript.ascent*self.subscript_scale - self.subscript_shift)
            self.descent = max(self.descent, self.subscript.descent*self.subscript_scale + self.subscript_shift)
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        if self.exponent is not None:
            with saved(ctx):
                ctx.translate(0, self.superscript_shift)
                ctx.scale(self.exponent_scale, self.exponent_scale)
                self.exponent.draw(ctx, cursor, widget_transform)
        if self.subscript is not None:
            with saved(ctx):
                ctx.translate(0, self.subscript_shift)
                ctx.scale(self.subscript_scale, self.subscript_scale)
                self.subscript.draw(ctx, cursor, widget_transform)

    @classmethod
    def make_greedily(cls, left, right):
        return cls(exponent=right)

    def accept_selection(self, selection, direction):
        if direction is Direction.LEFT:
            self._selection_acceptor.elements[0:0] = selection
        else:
            self._selection_acceptor.elements.extend(selection)
        for x in selection:
            x.parent = self._selection_acceptor

    def dissolve(self, cursor, caller):
        if len(self.lists) == 1:
            return super().dissolve(cursor, caller)
        self.lists.remove(caller)
        if caller is self.exponent:
            self.exponent = None
            self.parent.insert_elementlist(caller, cursor, self.index_in_parent+1, False)
        elif caller is self.subscript:
            self.subscript = None
            self.parent.insert_elementlist(caller, cursor, self.index_in_parent, True)

    def to_latex(self):
        res = ""
        if self.subscript is not None:
            res += "_{" + self.subscript.to_latex() + "}"
        if self.exponent is not None:
            res += "^{" + self.exponent.to_latex() + "}"
        return res
