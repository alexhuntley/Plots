from . import elements
from . import element
from plots.utils import saved, font_metrics

class Frac(element.Element):
    vertical_separation = 4
    greedy_insert_right = greedy_insert_left = True

    def __init__(self, numerator=None, denominator=None, parent=None):
        super().__init__(parent)
        self.numerator = elements.ElementList(numerator, self)
        self.denominator = elements.ElementList(denominator, self)
        self.lists = [self.numerator, self.denominator]
        self.cursor_acceptor = self.denominator

    def __repr__(self):
        return f"Frac(numerator={self.numerator}, denominator={self.denominator})"

    def compute_metrics(self, ctx, metric_ctx):
        self.numerator.compute_metrics(ctx, metric_ctx)
        self.denominator.compute_metrics(ctx, metric_ctx)
        self.width = max(self.numerator.width, self.denominator.width)

        font_ascent = font_metrics(ctx).ascent
        self.bar_height = font_ascent * 0.3
        self.ascent = self.numerator.ascent + self.numerator.descent + \
            self.bar_height + self.vertical_separation//2
        self.descent = self.denominator.ascent + self.denominator.descent + \
            self.vertical_separation//2 - self.bar_height
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        with saved(ctx):
            ctx.translate(0, -self.bar_height)
            ctx.move_to(0,0)
            ctx.set_line_width(1)
            ctx.line_to(self.width, 0)
            ctx.stroke()
            ctx.move_to(0,0)
            with saved(ctx):
                ctx.translate(self.width//2 - self.numerator.width//2,
                              -self.vertical_separation//2 - self.numerator.descent)
                self.numerator.draw(ctx, cursor, widget_transform)
            with saved(ctx):
                ctx.translate(self.width//2 - self.denominator.width//2,
                              self.vertical_separation//2 + self.denominator.ascent)
                self.denominator.draw(ctx, cursor, widget_transform)

    def accept_selection(self, selection, direction):
        self.numerator.elements.extend(selection)
        for x in selection:
            x.parent = self.numerator

    @classmethod
    def make_greedily(cls, left, right):
        return cls(numerator=left, denominator=right)

    def to_glsl(self):
        num_body, num_expr = self.numerator.to_glsl()
        den_body, den_expr = self.denominator.to_glsl()
        return num_body + den_body, f"({num_expr})/({den_expr})"

    def to_latex(self):
        return "\\frac{" + self.numerator.to_latex() + "}{" + self.denominator.to_latex() + "}"
