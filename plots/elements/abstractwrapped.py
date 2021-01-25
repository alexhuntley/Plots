from . import elements
from . import element
from plots.utils import saved, Text

class AbstractWrapped(element.Element):
    """Abstract class for elements consisting of an ElementList
sandwiched between two characters (e.g. Abs, Floor, Ceil).
    """
    def __init__(self, argument, left_bar, right_bar, parent=None):
        super().__init__(parent)
        self.argument = elements.ElementList(argument, self)
        self.left_bar_char = left_bar
        self.right_bar_char = right_bar
        self.lists = [self.argument]
        self.cursor_acceptor = self.argument
        self.class_name = type(self).__name__

    def __repr__(self):
        return f"{self.class_name}({self.argument})"

    def compute_metrics(self, ctx, metric_ctx):
        self.argument.compute_metrics(ctx, metric_ctx)
        self.left_bar = Text(self.left_bar_char, ctx)
        self.right_bar = Text(self.right_bar_char, ctx)
        self.width = self.argument.width + \
            self.left_bar.width + self.right_bar.width
        self.ascent = self.argument.ascent
        self.descent = self.argument.descent
        super().compute_metrics(ctx, metric_ctx)

    def draw_bar(self, ctx, bar):
        bar_height = bar.ink_rect.height
        scale_factor = max(1, (self.ascent + self.descent)/bar_height)
        with saved(ctx):
            ctx.translate(0, -self.ascent)
            ctx.scale(1, scale_factor)
            ctx.translate(0, -bar.ink_rect.y)
            ctx.move_to(0, 0)
            bar.draw(ctx)

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        self.draw_bar(ctx, self.left_bar)
        ctx.translate(self.left_bar.width, 0)
        self.argument.draw(ctx, cursor, widget_transform)
        ctx.translate(self.argument.width, 0)
        self.draw_bar(ctx, self.right_bar)

    def accept_selection(self, selection, direction):
        self.argument.elements.extend(selection)
        for x in selection:
            x.parent = self.argument

    def to_glsl(self):
        arg_body, arg_expr = self.argument.to_glsl()
        return arg_body, f"{self.class_name.lower()}({arg_expr})"

    def to_latex(self):
        return rf"\{self.class_name.lower()}{{{self.argument.to_latex()}}}"
