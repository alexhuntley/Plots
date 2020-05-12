from collections import namedtuple
from gi.repository import Gtk, Gdk, cairo, Pango, PangoCairo
from enum import Enum

desc = Pango.font_description_from_string("Latin Modern Math 20")
DEFAULT_ASCENT = 10
DEBUG = False
dpi = PangoCairo.font_map_get_default().get_resolution()

class Editor(Gtk.DrawingArea):
    def __init__ (self):
        super().__init__()
        self.cursor = Cursor()
        self.test_expr = ElementList([Paren('('), Atom('a'), Paren(')'), Atom('b'), Atom('c'), Expt([Atom('dasdlaksjdkl')]),
             Paren('('),
             Frac([Radical([Frac([Atom('b')], [Atom('c')]), Atom('y')], [Atom('3')])], [Atom('cab'), Radical([Atom('ab')])]),
             Paren(')')])
        self.test_expr.elements[1].handle_cursor(self.cursor, Direction.NONE)
        self.props.can_focus = True
        self.connect("key-press-event", self.on_key_press)

    def do_draw_cb(self, widget, ctx):
        scale = 2
        ctx.scale(scale, scale)
        self.test_expr.compute_metrics(ctx, MetricContext(self.cursor))
        ctx.translate(0, self.test_expr.ascent)
        self.test_expr.draw(ctx)
        self.set_size_request(self.test_expr.width*scale,
                              (self.test_expr.ascent + self.test_expr.descent)*scale)

    def on_key_press(self, widget, event):
        try:
            direction = Direction(event.keyval)
            self.cursor.handle_movement(direction)
            self.queue_draw()
        except ValueError:
            pass

class MetricContext():
    def __init__(self, cursor=None):
        self.prev_ascent = DEFAULT_ASCENT
        self.paren_stack = []
        self.cursor = cursor

class Cursor():
    def __init__(self):
        self.owner = None

    def reparent(self, new_parent):
        if self.owner:
            self.owner.lose_cursor()
        self.owner = new_parent

    def handle_movement(self, direction):
        self.owner.handle_cursor(self, direction)

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

class Direction(Enum):
    UP = Gdk.KEY_Up
    DOWN = Gdk.KEY_Down
    LEFT = Gdk.KEY_Left
    RIGHT = Gdk.KEY_Right
    NONE = 0

class Element():
    """Abstract class describing an element of an equation.

    Implementations must provide ascent, descent
    and width properties, compute_metrics(ctx, prev_ascent) and draw(ctx)."""

    def __init__(self, parent):
        self.parent = parent
        self.index_in_parent = None
        self.has_cursor = False

    def compute_metrics(self, ctx, metric_ctx):
        """To be run at the end of overriding methods, if they
        wish to have parens scale around them"""
        stack = metric_ctx.paren_stack
        if stack:
            stack[-1].ascent = max(self.ascent, stack[-1].ascent)
            stack[-1].descent = max(self.descent, stack[-1].descent)

    def draw(self, ctx):
        if DEBUG or self.has_cursor:
            ctx.set_line_width(0.5)
            ctx.set_source_rgba(1, 0, 1 if self.has_cursor else 0, 0.6)
            ctx.rectangle(0, -self.ascent, self.width, self.ascent + self.descent)
            ctx.stroke()
            ctx.set_source_rgba(0,0,0)
        ctx.move_to(0,0)

    def lose_cursor(self):
        self.has_cursor = False

    def handle_cursor(self, cursor, direction, giver=None):
        if direction is Direction.NONE or not self.has_cursor:
            cursor.reparent(self)
            self.has_cursor = True
        else:
            if self.parent:
                self.parent.handle_cursor(cursor, direction, self)
            else:
                print(self)

    def parent_handle_cursor(self, cursor, direction):
        if self.parent:
            self.parent.handle_cursor(cursor, direction, self)

class ElementList(Element):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.elements = elements or []
        for e in self.elements:
            e.parent = self

    def compute_metrics(self, ctx, metric_ctx):
        self.ascent = self.descent = self.width = 0
        metric_ctx = MetricContext(metric_ctx.cursor)
        for i, e in enumerate(self.elements):
            e.index_in_parent = i
            e.compute_metrics(ctx, metric_ctx)
            self.ascent = max(self.ascent, e.ascent)
            self.descent = max(self.descent, e.descent)
            self.width += e.width
            metric_ctx.prev_ascent = e.ascent

    def draw_cursor(self, ctx):
        ctx.set_source_rgb(0, 0, 0)
        ctx.move_to(0, 0)
        ctx.rel_line_to(0, -DEFAULT_ASCENT)
        ctx.rel_move_to(0, DEFAULT_ASCENT)
        ctx.stroke()

    def draw(self, ctx):
        super().draw(ctx)
        ctx.save()
        ctx.move_to(0,0)
        self.cursor_pos = 2
        for i, e in enumerate(self.elements):
            ctx.move_to(0, 0)
            e.draw(ctx)
            if i == self.cursor_pos:
                self.draw_cursor(ctx)
            ctx.translate(e.width, 0)
        if self.cursor_pos == len(self.elements):
            self.draw_cursor(ctx)
        ctx.restore()

    def handle_cursor(self, cursor, direction, giver=None):
        if (direction is Direction.UP or direction is Direction.DOWN) and self.parent and giver:
            self.parent.handle_cursor(cursor, direction, giver=self)
        elif giver:
            i = giver.index_in_parent
            if direction is Direction.LEFT:
                if i > 0:
                    self.elements[i-1].handle_cursor(cursor, direction)
                elif self.parent:
                    self.parent.handle_cursor(cursor, direction, self)
            elif direction is Direction.RIGHT:
                if i < len(self.elements) - 1:
                    self.elements[i+1].handle_cursor(cursor, direction)
                elif self.parent:
                    self.parent.handle_cursor(cursor, direction, self)
            elif self.parent:
                self.parent.handle_cursor(cursor, direction, self)
        elif direction is Direction.LEFT:
            self.elements[-1].handle_cursor(cursor, direction)
        else:
            self.elements[0].handle_cursor(cursor, direction)

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
        self.exponent.compute_metrics(ctx, metric_ctx)
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

    def handle_cursor(self, cursor, direction, giver=None):
        if giver is self.exponent:
            self.parent.handle_cursor(cursor, direction, self)
        else:
            self.exponent.handle_cursor(cursor, direction)

class Frac(Element):
    vertical_separation = 4
    def __init__(self, numerator=None, denominator=None, parent=None):
        super().__init__(parent)
        self.numerator = ElementList(numerator, self)
        self.denominator = ElementList(denominator, self)

    def compute_metrics(self, ctx, metric_ctx):
        self.numerator.compute_metrics(ctx, metric_ctx)
        self.denominator.compute_metrics(ctx, metric_ctx)
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

    def handle_cursor(self, cursor, direction, giver=None):
        if giver is self.numerator and direction is Direction.DOWN:
            self.denominator.handle_cursor(cursor, direction)
        elif giver is self.denominator and direction is Direction.UP:
            self.numerator.handle_cursor(cursor, direction)
        elif giver is self.numerator or giver is self.denominator:
            self.parent.handle_cursor(cursor, direction, self)
        else:
            if direction is Direction.UP:
                self.denominator.handle_cursor(cursor, direction)
            else:
                self.numerator.handle_cursor(cursor, direction)

class Radical(Element):
    def __init__(self, radicand, index=None, parent=None):
        super().__init__(parent)
        self.radicand = ElementList(radicand, self)
        self.index = ElementList(index, self)
        self.overline_space = 4

    def compute_metrics(self, ctx, metric_ctx):
        self.radicand.compute_metrics(ctx, metric_ctx)
        self.index.compute_metrics(ctx, metric_ctx)
        self.symbol = PangoCairo.create_layout(ctx)
        self.symbol.set_text("√")
        self.symbol.set_font_description(desc)
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

    def handle_cursor(self, cursor, direction, giver=None):
        if giver is self.radicand:
            print(self.parent)
            self.parent_handle_cursor(cursor, direction)
        else:
            self.radicand.handle_cursor(cursor, direction)

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
        self.layout.set_font_description(desc)
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
