from . import elements
from . import element
from plots.utils import saved, Text

class Abs(element.Element):
    def __init__(self, argument, parent=None):
        super().__init__(parent)
        self.argument = elements.ElementList(argument, self)
        self.lists = [self.argument]
        self.cursor_acceptor = self.argument

    def __repr__(self):
        return f"Abs({self.argument})"

    def compute_metrics(self, ctx, metric_ctx):
        self.argument.compute_metrics(ctx, metric_ctx)
        self.bar = Text("|", ctx)
        self.width = self.argument.width + 2*self.bar.width
        self.ascent = self.argument.ascent
        self.descent = self.argument.descent
        super().compute_metrics(ctx, metric_ctx)

    def draw_bar(self, ctx):
        bar_height = self.bar.ink_rect.height
        scale_factor = max(1, (self.ascent + self.descent)/bar_height)
        with saved(ctx):
            ctx.translate(0, -self.ascent)
            ctx.scale(1, scale_factor)
            ctx.translate(0, -self.bar.ink_rect.y)
            ctx.move_to(0, 0)
            self.bar.draw(ctx)

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        self.draw_bar(ctx)
        ctx.translate(self.bar.width, 0)
        self.argument.draw(ctx, cursor, widget_transform)
        ctx.translate(self.argument.width, 0)
        self.draw_bar(ctx)

    def accept_selection(self, selection, direction):
        self.argument.elements.extend(selection)
        for x in selection:
            x.parent = self.argument

    def to_glsl(self):
        arg_body, arg_expr = self.argument.to_glsl()
        return arg_body, f"abs({arg_expr})"

    def to_latex(self):
        return f"\\abs{{{self.argument.to_latex()}}}"
