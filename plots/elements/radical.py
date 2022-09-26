from . import elements
from . import element
from plots.utils import saved, Text

class Radical(element.Element):
    index_y_shift = 16
    index_x_shift = 16
    index_scale = 0.8

    def __init__(self, radicand, index=None, parent=None):
        super().__init__(parent)
        self.radicand = elements.ElementList(radicand, self)
        if index is not None:
            self.index = elements.ElementList(index, self)
            self.lists = [self.index, self.radicand]
        else:
            self.index = None
            self.lists = [self.radicand]
        self.overline_space = 4

    def __repr__(self):
        return f"Radical({self.radicand}, index={self.index})"

    def compute_metrics(self, ctx, metric_ctx):
        self.radicand.compute_metrics(ctx, metric_ctx)
        self.symbol = Text("√", ctx)
        self.width = self.radicand.width + self.symbol.width
        self.main_ascent = self.ascent = max(self.symbol.ascent, self.radicand.ascent + self.overline_space)
        self.descent = self.radicand.descent
        if self.index is not None:
            self.index.compute_metrics(ctx, metric_ctx)
            self.width += self.index.width*self.index_scale - self.index_x_shift
            self.ascent = max(self.main_ascent,
                              (self.index.ascent + self.index.descent)*self.index_scale \
                              - self.index_y_shift + self.main_ascent)

        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)

        if self.index is not None:
            with saved(ctx):
                ctx.translate(0, -self.main_ascent + self.index_y_shift -self.index.descent)
                ctx.scale(self.index_scale, self.index_scale)
                ctx.move_to(0, 0)
                self.index.draw(ctx, cursor, widget_transform)
            ctx.translate(self.index.width*self.index_scale - self.index_x_shift, 0)

        symbol_size = self.symbol.ink_rect.height
        scale_factor = max(1, (self.main_ascent + self.descent)/symbol_size)
        with saved(ctx):
            ctx.translate(0, -self.main_ascent)
            ctx.scale(1, scale_factor)
            ctx.translate(0, -self.symbol.ink_rect.y)
            ctx.move_to(0, 0)
            self.symbol.draw(ctx)

        ctx.translate(self.symbol.width, 0)
        ctx.set_line_width(1)
        ctx.move_to(0, -self.main_ascent + ctx.get_line_width())
        ctx.rel_line_to(self.radicand.width, 0)
        ctx.stroke()
        ctx.move_to(0,0)
        self.radicand.draw(ctx, cursor, widget_transform)

    def to_glsl(self):
        radicand_body, radicand_expr = self.radicand.to_glsl()
        if self.index:
            index_body, index_expr = self.index.to_glsl()
            return radicand_body + index_body, f"pow({radicand_expr}, 1.0/({index_expr}))"
        else:
            return radicand_body, f"sqrt({radicand_expr})"

    def to_latex(self):
        if self.index:
            return "\\sqrt[" + self.index.to_latex() + "]{" + self.radicand.to_latex() + "}"
        else:
            return "\\sqrt{" + self.radicand.to_latex() + "}"
