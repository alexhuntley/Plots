from collections import namedtuple
from gi.repository import Gtk, Gdk, cairo, Pango, PangoCairo

desc = Pango.font_description_from_string("MathJax_Math 20")
desc_main = Pango.font_description_from_string("MathJax_Main 20")
desc = desc_main = Pango.font_description_from_string("Latin Modern Math 20")
DEFAULT_ASCENT = 10
DEBUG = False
dpi = PangoCairo.font_map_get_default().get_resolution()

def italify_string(s):
    def italify_char(c):
        if c == 'h':
            return 'ℎ'
        if c.islower():
            return chr(ord(c) - 0x61 + 0x1d44e)
        if c.isupper():
            return chr(ord(c) - 0x41 + 0x1d434)
        return c
    return "".join(italify_char(c) for c in s)

class Element():
    """Abstract class describing an element of an equation.

    Implementations must provide ascent, descent
    and width properties, compute_metrics(ctx, prev_ascent) and draw(ctx)."""

    def __init__(self, parent):
        self.parent = parent

    def compute_metrics(self, ctx, metric_ctx):
        """To be run at the end of overriding methods, if they
        wish to have parens scale around them"""
        stack = metric_ctx.paren_stack
        if stack:
            stack[-1].ascent = max(self.ascent, stack[-1].ascent)
            stack[-1].descent = max(self.descent, stack[-1].descent)

    def draw(self, ctx):
        if DEBUG:
            ctx.set_line_width(0.5)
            ctx.set_source_rgba(1,0,0,0.6)
            ctx.rectangle(0, -self.ascent, self.width, self.ascent + self.descent)
            ctx.stroke()
            ctx.set_source_rgba(0,0,0)
        ctx.move_to(0,0)

class ElementList(Element):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.elements = elements or []
        if parent:
            for e in self.elements:
                e.parent = parent

    def compute_metrics(self, ctx, metric_ctx=None):
        self.ascent = self.descent = self.width = 0
        class MetricContext():
            def __init__(self):
                self.prev_ascent = DEFAULT_ASCENT
                self.paren_stack = []
        metric_ctx = MetricContext()
        for e in self.elements:
            e.compute_metrics(ctx, metric_ctx)
            self.ascent = max(self.ascent, e.ascent)
            self.descent = max(self.descent, e.descent)
            self.width += e.width
            metric_ctx.prev_ascent = e.ascent

    def draw(self, ctx):
        ctx.save()
        ctx.move_to(0,0)
        for e in self.elements:
            e.draw(ctx)
            ctx.translate(e.width, 0)
        ctx.restore()

class Atom(Element):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name

    def compute_metrics(self, ctx, metric_ctx):
        self.layout = PangoCairo.create_layout(ctx)
        self.layout.set_text(italify_string(self.name))
        self.layout.set_font_description(desc)
        self.width, self.height = self.layout.get_pixel_size()
        self.baseline = self.layout.get_baseline()//Pango.SCALE
        self.ascent = self.baseline
        self.descent = self.height - self.baseline
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx):
        super().draw(ctx)
        ctx.move_to(0, -self.baseline)
        PangoCairo.show_layout(ctx, self.layout)

class Expt(Element):
    def __init__(self, exponent=None, parent=None):
        super().__init__(parent)
        self.exponent = ElementList(exponent, self)
        self.exponent_scale = 0.8

    def compute_metrics(self, ctx, metric_ctx):
        self.exponent.compute_metrics(ctx, DEFAULT_ASCENT)
        self.child_shift = -self.exponent.descent*self.exponent_scale - metric_ctx.prev_ascent//2 # -ve y is up
        self.width = self.exponent.width*self.exponent_scale
        self.ascent = self.exponent.ascent*self.exponent_scale - self.child_shift
        self.descent = max(0, self.exponent.descent*self.exponent_scale + self.child_shift)
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx):
        super().draw(ctx)
        ctx.save()
        ctx.translate(0, self.child_shift)
        ctx.scale(self.exponent_scale, self.exponent_scale)
        self.exponent.draw(ctx)
        ctx.restore()

class Frac(Element):
    vertical_separation = 4
    def __init__(self, numerator=None, denominator=None, parent=None):
        super().__init__(parent)
        self.numerator = ElementList(numerator, self)
        self.denominator = ElementList(denominator, self)

    def compute_metrics(self, ctx, metric_ctx):
        self.numerator.compute_metrics(ctx)
        self.denominator.compute_metrics(ctx)
        self.width = max(self.numerator.width, self.denominator.width)
        font = PangoCairo.font_map_get_default().load_font(PangoCairo.create_context(ctx), desc)
        font_ascent = font.get_metrics().get_ascent()//Pango.SCALE
        self.bar_height = int(font_ascent * (dpi/72.0) * 0.3)
        self.ascent = self.numerator.ascent + self.numerator.descent + \
            self.bar_height + self.vertical_separation//2
        self.descent = self.denominator.ascent + self.denominator.descent + \
            self.vertical_separation//2 - self.bar_height
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx):
        super().draw(ctx)
        ctx.save()
        ctx.translate(0, -self.bar_height)
        ctx.move_to(0,0)
        ctx.set_line_width(1)
        ctx.line_to(self.width, 0)
        ctx.stroke()
        ctx.move_to(0,0)
        ctx.save()
        ctx.translate(self.width//2 - self.numerator.width//2,
                      -self.vertical_separation//2 - self.numerator.descent)
        self.numerator.draw(ctx)
        ctx.restore()
        ctx.save()
        ctx.translate(self.width//2 - self.denominator.width//2,
                      self.vertical_separation//2 + self.denominator.ascent)
        self.denominator.draw(ctx)
        ctx.restore()
        ctx.restore()

class Radical(Element):
    def __init__(self, radicand, index=None, parent=None):
        super().__init__(parent)
        self.radicand = ElementList(radicand)
        self.index = ElementList(index)
        self.overline_space = 4

    def compute_metrics(self, ctx, metric_ctx):
        self.radicand.compute_metrics(ctx, None)
        self.index.compute_metrics(ctx, None)
        self.symbol = PangoCairo.create_layout(ctx)
        self.symbol.set_text("√")
        self.symbol.set_font_description(desc_main)
        self.width = self.radicand.width + self.symbol.get_pixel_size().width
        self.ascent = max(self.symbol.get_baseline()//Pango.SCALE,
                          self.radicand.ascent + self.overline_space)
        self.descent = self.radicand.descent
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx):
        super().draw(ctx)
#        ctx.move_to(0, -self.ascent)
        extents = self.symbol.get_pixel_extents()
        symbol_size = extents.ink_rect.height
        scale_factor = max(1, (self.ascent + self.descent)/symbol_size)
        ctx.save()
        ctx.translate(0, -self.ascent)
        ctx.scale(1, scale_factor)
        ctx.translate(0, -extents.ink_rect.y)
        ctx.move_to(0, 0)
        PangoCairo.show_layout(ctx, self.symbol)
        ctx.restore()

        ctx.translate(self.symbol.get_pixel_size().width, 0)
        ctx.set_source_rgb(0,0,0)
        ctx.set_line_width(1)
        ctx.move_to(0, -self.ascent + ctx.get_line_width())
        ctx.rel_line_to(self.radicand.width, 0)
        ctx.stroke()
        ctx.move_to(0,0)
        self.radicand.draw(ctx)

class Paren(Element):
    def __init__(self, char, parent=None):
        super().__init__(parent)
        if len(char) != 1:
            raise ValueError("{!r} is not a valid paren".format(char))
        if char in "({[":
            self.left = True
        elif char in "]})":
            self.left = False
        else:
            raise ValueError("{!r} is not a valid paren".format(char))
        self.char = char

    def compute_metrics(self, ctx, metric_ctx):
        self.layout = PangoCairo.create_layout(ctx)
        self.layout.set_text(self.char)
        self.layout.set_font_description(desc_main)
        self.width, self.height = self.layout.get_pixel_size()
        self.baseline = self.layout.get_baseline()//Pango.SCALE
        self.ascent = self.baseline
        self.descent = self.height - self.baseline

        if self.left:
            metric_ctx.paren_stack.append(self)
        else:
            match = metric_ctx.paren_stack.pop()
            self.ascent = match.ascent
            self.descent = match.descent
            super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx):
        super().draw(ctx)
        # print([(r.x, r.y, r.width, r.height) for r in self.layout.get_pixel_extents()])
        # print(self.layout.get_pixel_extents())
        extents = self.layout.get_pixel_extents()
        symbol_size = extents.ink_rect.height
        scale_factor = max(1, (self.ascent + self.descent)/symbol_size)
        ctx.save()
        ctx.scale(1, scale_factor)
        ctx.translate(0, -self.ascent/scale_factor-extents.ink_rect.y)
        ctx.move_to(0, 0)
        PangoCairo.show_layout(ctx, self.layout)
        ctx.restore()



test_frac = ElementList([Atom('a'), Frac([Atom('b')], [Atom('c')])])
