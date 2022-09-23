from . import elements
from . import element
from . import atom
from plots.utils import saved, Text

class Sum(element.Element):
    child_scale = 0.7
    bottom_padding = 4
    glsl_var_counter = 0

    def __init__(self, parent=None, char="∑", top=None, bottom=None):
        super().__init__(parent=parent)
        self.top = elements.ElementList(top or [], self)
        self.bottom = elements.ElementList(bottom or [atom.BinaryOperatorAtom("=")], self)
        self.lists = [self.top, self.bottom]
        self.default_list = self.bottom
        self.char = char

    def __repr__(self):
        return f"Sum(char={self.char}, top={self.top}, bottom={self.bottom})"

    def compute_metrics(self, ctx, metric_ctx):
        self.symbol = Text(self.char, ctx, scale=1.5)
        self.top.compute_metrics(ctx, metric_ctx)
        self.bottom.compute_metrics(ctx, metric_ctx)
        self.width = max(self.symbol.width, self.top.width*self.child_scale,
                         self.bottom.width*self.child_scale)
        self.ascent = self.symbol.ascent + self.child_scale*self.top.height
        self.descent = self.symbol.descent + \
            self.child_scale*self.bottom.height + self.bottom_padding
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        with saved(ctx):
            ctx.translate(self.width/2 - self.symbol.width/2, 0)
            self.symbol.draw_at_baseline(ctx)
        with saved(ctx):
            ctx.translate(self.width/2, -self.symbol.ascent)
            ctx.scale(self.child_scale, self.child_scale)
            ctx.translate(-self.top.width/2, -self.top.descent)
            self.top.draw(ctx, cursor, widget_transform)
        with saved(ctx):
            ctx.translate(self.width/2, self.symbol.descent + self.bottom_padding)
            ctx.scale(self.child_scale, self.child_scale)
            ctx.translate(-self.bottom.width/2, self.bottom.ascent)
            self.bottom.draw(ctx, cursor, widget_transform)

    def to_glsl(self, arg_body, arg_expr):
        init_body, init_expr = self.bottom.to_glsl()
        end_body, end_expr = self.top.to_glsl()
        var = init_expr.split('=')[0].strip()
        sum_var = f"sum{Sum.glsl_var_counter}"
        Sum.glsl_var_counter += 1
        if Sum.glsl_var_counter > 100000:
            Sum.glsl_var_counter = 0
        if self.char == "∑":
            init = 0.0
            op = "+="
        elif self.char == "∏":
            init = 1.0
            op = "*="
        body = f"""
        {init_body}
        {end_body}
        float {sum_var} = {init};
        for (float {init_expr}; {var} <= {end_expr}; {var}++) {{
            {arg_body}
            {sum_var} {op} {arg_expr};
        }}"""
        return body, sum_var

    def to_latex(self):
        if self.char == "∑":
            return r"\sum_{" + self.bottom.to_latex() + "}^{" + self.top.to_latex() + "}"
        elif self.char == "∏":
            return r"\prod_{" + self.bottom.to_latex() + "}^{" + self.top.to_latex() + "}"
