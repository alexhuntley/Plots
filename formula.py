import re
from itertools import count
from collections import namedtuple
from gi.repository import GLib, Gtk, Gdk, cairo, Pango, PangoCairo
from enum import Enum

desc = Pango.font_description_from_string("Latin Modern Math 20")
DEBUG = False
dpi = PangoCairo.font_map_get_default().get_resolution()

GREEK_LETTERS = {
    'Alpha': 'Α',
    'Beta': 'Β',
    'Chi': 'Χ',
    'Delta': 'Δ',
    'Epsilon': 'Ε',
    'Eta': 'Η',
    'Gamma': 'Γ',
    'Iota': 'Ι',
    'Kappa': 'Κ',
    'Lambda': 'Λ',
    'Mu': 'Μ',
    'Nu': 'Ν',
    'Omega': 'Ω',
    'Omicron': 'Ο',
    'Phi': 'Φ',
    'Pi': 'Π',
    'Psi': 'Ψ',
    'Rho': 'Ρ',
    'Sigma': 'Σ',
    'Tau': 'Τ',
    'Theta': 'Θ',
    'Upsilon': 'Υ',
    'Xi': 'Ξ',
    'Zeta': 'Ζ',
    'alpha': 'α',
    'beta': 'β',
    'chi': 'χ',
    'delta': 'δ',
    'epsilon': 'ε',
    'eta': 'η',
    'gamma': 'γ',
    'iota': 'ι',
    'kappa': 'κ',
    'lambda': 'λ',
    'mu': 'μ',
    'nu': 'ν',
    'omega': 'ω',
    'omicron': 'ο',
    'phi': 'φ',
    'pi': 'π',
    'psi': 'ψ',
    'rho': 'ρ',
    'sigma': 'σ',
    'tau': 'τ',
    'theta': 'θ',
    'upsilon': 'υ',
    'xi': 'ξ',
    'zeta': 'ζ'
}
GREEK_REGEXES = GREEK_LETTERS.copy()
GREEK_REGEXES['(?<![EUeu])psi'] = GREEK_REGEXES.pop('psi')

class Editor(Gtk.DrawingArea):
    def __init__ (self):
        super().__init__()
        self.cursor = Cursor()
        self.test_expr = ElementList([Paren('('), Radical([]), OperatorAtom('sin'), Atom('a'), Paren(')'), Atom('b'), Atom('c'), Expt([Atom('d')]),
             Paren('('),
             Frac([Radical([Frac([Atom('b')], [Atom('c')]), Atom('y')], [Atom('3')])], [Atom('c'), Radical([Atom('a')])]),
             Paren(')')])
        self.expr = ElementList()
        self.expr.handle_cursor(self.cursor, Direction.NONE)
        self.props.can_focus = True
        self.connect("key-press-event", self.on_key_press)
        self.connect('draw', self.do_draw_cb)
        self.blink_source = None
        self.restart_blink_sequence()

    def do_draw_cb(self, widget, ctx):
        scale = 1
        ctx.translate(4,4) # a bit of padding
        ctx.scale(scale, scale)
        self.expr.compute_metrics(ctx, MetricContext(self.cursor))
        ctx.translate(0, self.expr.ascent)
        self.expr.draw(ctx, self.cursor)
        self.set_size_request(self.expr.width*scale,
                              (self.expr.ascent + self.expr.descent)*scale)

    def blink_cursor_cb(self):
        self.cursor.visible = not self.cursor.visible
        self.queue_draw()
        return True

    def restart_blink_sequence(self):
        self.cursor.visible = True
        if self.blink_source:
            GLib.source_remove(self.blink_source)
        def cb():
            self.blink_source = GLib.timeout_add(Cursor.BLINK_DELAY, self.blink_cursor_cb)
            return False
        self.blink_source = GLib.timeout_add(Cursor.BLINK_DELAY, self.blink_cursor_cb)

    def on_key_press(self, widget, event):
        self.restart_blink_sequence()
        if DEBUG:
            print(Gdk.keyval_name(event.keyval))
        char = chr(Gdk.keyval_to_unicode(event.keyval))
        if char.isalnum():
            self.cursor.insert(Atom(char))
            self.queue_draw()
            return
        if char in "+-*=":
            translation = str.maketrans("-*", "−×")
            self.cursor.insert(BinaryOperatorAtom(char.translate(translation)))
            self.queue_draw()
            return
        if char in "!'.":
            translation = str.maketrans("'", "′")
            self.cursor.insert(Atom(char.translate(translation)))
            self.queue_draw()
            return
        if char in "()[]{}":
            self.cursor.insert(Paren(char))
            self.queue_draw()
            return
        if event.keyval == Gdk.KEY_BackSpace:
            self.cursor.backspace(Direction.LEFT)
            self.queue_draw()
            return
        if event.keyval == Gdk.KEY_Delete:
            self.cursor.backspace(Direction.RIGHT)
            self.queue_draw()
            return
        if event.keyval == Gdk.KEY_slash:
            self.cursor.greedy_insert(Frac)
            self.queue_draw()
            return
        if char == "^":
            self.cursor.greedy_insert(Expt)
            self.queue_draw()
            return
        try:
            direction = Direction(event.keyval)
            self.cursor.handle_movement(direction)
            self.queue_draw()
            return
        except ValueError:
            pass

class saved():
    def __init__(self, ctx):
        self.ctx = ctx

    def __enter__(self):
        self.ctx.save()

    def __exit__(self ,exc_type, exc_val, exc_tb):
        self.ctx.restore()
        return False

class MetricContext():
    def __init__(self, cursor=None):
        self.prev = None
        self.paren_stack = []
        self.cursor = cursor

class Cursor():
    WIDTH = 1
    BLINK_DELAY = 600

    def __init__(self):
        self.owner = None
        self.visible = True

    def reparent(self, new_parent):
        if self.owner:
            self.owner.lose_cursor()
        self.owner = new_parent

    def handle_movement(self, direction):
        self.owner.handle_cursor(self, direction)

    def backspace(self, direction):
        self.owner.backspace(self, direction=direction)

    def insert(self, element):
        self.owner.insert(element, self)

    def greedy_insert(self, cls):
        self.owner.greedy_insert(cls, self)

def italify_string(s):
    def italify_char(c):
        if c == 'h':
            return 'ℎ'
        # lowercase latin
        if c.islower() and c.isascii():
            return chr(ord(c) - 0x61 + 0x1d44e)
        # uppercase latin
        if c.isupper() and c.isascii():
            return chr(ord(c) - 0x41 + 0x1d434)
        # lowercase greek (n.b. don't italify uppers)
        if 0x3b1 <= ord(c) < 0x3b1 + 18:
            return chr(ord(c) - 0x3b1 + 0x1d6fc)
        return c
    return "".join(italify_char(c) for c in s)

def deitalify_char(c):
    if c == 'ℎ':
        return 'h'
    if 0x1d44e <= ord(c) < 0x1d44e + 26:
        return chr(ord(c) - 0x1d44e + 0x61)
    if 0x1d434 <= ord(c) < 0x1d434 + 26:
        return chr(ord(c) - 0x1d434 + 0x41)
    return c

def deitalify_string(s):
    return "".join(deitalify_char(c) for c in s)

class Direction(Enum):
    UP = Gdk.KEY_Up
    DOWN = Gdk.KEY_Down
    LEFT = Gdk.KEY_Left
    RIGHT = Gdk.KEY_Right
    NONE = 0

class Element():
    """Abstract class describing an element of an equation.

    Implementations must provide ascent, descent
    and width properties, compute_metrics(ctx, metric_ctx) and draw(ctx, cursor)."""

    wants_cursor = True
    h_spacing = 2

    def __init__(self, parent):
        self.parent = parent
        self.index_in_parent = None
        self.has_cursor = False

    def font_metrics(self, ctx):
        text = Text("x", ctx)
        return text

    def compute_metrics(self, ctx, metric_ctx):
        """To be run at the end of overriding methods, if they
        wish to have parens scale around them"""
        stack = metric_ctx.paren_stack
        if stack:
            stack[-1].ascent = max(self.ascent, stack[-1].ascent)
            stack[-1].descent = max(self.descent, stack[-1].descent)

    def draw(self, ctx, cursor):
        if DEBUG:
            ctx.set_line_width(0.5)
            ctx.set_source_rgba(1, 0, 1 if self.has_cursor else 0, 0.6)
            ctx.rectangle(0, -self.ascent, self.width, self.ascent + self.descent)
            ctx.stroke()
        ctx.set_source_rgba(0,0,0)
        ctx.move_to(0,0)

    def lose_cursor(self):
        self.has_cursor = False

    def handle_cursor(self, cursor, direction, giver=None):
        if self.wants_cursor and (direction is Direction.NONE or not self.has_cursor):
            cursor.reparent(self)
            self.has_cursor = True
        elif self.parent:
            self.parent_handle_cursor(cursor, direction)

    def parent_handle_cursor(self, cursor, direction):
        if self.parent:
            self.parent.handle_cursor(cursor, direction, self)

class ElementList(Element):
    def __init__(self, elements=None, parent=None):
        super().__init__(parent)
        self.elements = elements or []
        self.cursor_pos = 0
        for e in self.elements:
            e.parent = self

    def __len__(self):
        return len(self.elements)

    def compute_metrics(self, ctx, metric_ctx):
        self.ascent = self.descent = self.width = 0
        metric_ctx = MetricContext(metric_ctx.cursor)
        metric_ctx.prev = self.font_metrics(ctx)
        for i, e in enumerate(self.elements):
            e.index_in_parent = i
            e.compute_metrics(ctx, metric_ctx)
            self.ascent = max(self.ascent, e.ascent)
            self.descent = max(self.descent, e.descent)
            self.width += e.width + 2*e.h_spacing
            metric_ctx.prev = e
        if not self.elements:
            self.ascent = self.font_metrics(ctx).ascent
            self.descent = self.font_metrics(ctx).descent
            self.width = self.font_metrics(ctx).width

    def draw_cursor(self, ctx, ascent, descent, cursor):
        if self.has_cursor and cursor.visible:
            ctx.set_source_rgb(0, 0, 0)
            ctx.set_line_width(max(ctx.device_to_user_distance(Cursor.WIDTH, Cursor.WIDTH)))
            ctx.move_to(0, descent-2)
            ctx.line_to(0, -ascent+2)
            ctx.move_to(0, 0)
            ctx.stroke()

    def draw(self, ctx, cursor):
        super().draw(ctx, cursor)
        with saved(ctx):
            ctx.move_to(0,0)
            for i, e in enumerate(self.elements):
                ctx.move_to(0,0)
                if i == self.cursor_pos:
                    ascent, descent = e.ascent, e.descent
                    if self.cursor_pos > 0:
                        ascent = max(ascent, self.elements[i-1].ascent)
                        descent = max(descent, self.elements[i-1].descent)
                    self.draw_cursor(ctx, ascent, descent, cursor)
                ctx.move_to(0, 0)
                ctx.translate(e.h_spacing, 0)
                with saved(ctx):
                    e.draw(ctx, cursor)
                ctx.move_to(0,0)
                ctx.translate(e.width + e.h_spacing, 0)
            if self.cursor_pos == len(self.elements) > 0:
                self.draw_cursor(ctx, self.elements[-1].ascent, self.elements[-1].descent, cursor)
            elif not self.elements:
                self.draw_cursor(ctx, self.ascent, self.descent, cursor)

    def move_cursor_to(self, cursor, index):
        cursor.reparent(self)
        self.has_cursor = True
        self.cursor_pos = index

    def handle_cursor(self, cursor, direction, giver=None):
        if (direction is Direction.UP or direction is Direction.DOWN) and self.parent and giver:
            self.parent.handle_cursor(cursor, direction, giver=self)
        elif giver:
            if direction is Direction.LEFT:
                self.move_cursor_to(cursor, giver.index_in_parent)
            elif direction is Direction.RIGHT:
                self.move_cursor_to(cursor, giver.index_in_parent+1)
            else:
                self.move_cursor_to(cursor, 0)
        elif self.has_cursor:
            i = self.cursor_pos
            if direction is Direction.LEFT and i > 0:
                if self.elements[i - 1].wants_cursor:
                    self.elements[i - 1].handle_cursor(cursor, direction)
                else:
                    self.move_cursor_to(cursor, i - 1)
            elif direction is Direction.RIGHT and i < len(self.elements):
                if self.elements[i].wants_cursor:
                    self.elements[i].handle_cursor(cursor, direction)
                else:
                    self.move_cursor_to(cursor, i+1)
            else:
                self.lose_cursor()
                self.parent_handle_cursor(cursor, direction)
        elif direction is Direction.LEFT:
            self.move_cursor_to(cursor, len(self.elements))
        else:
            self.move_cursor_to(cursor, 0)

    def backspace(self, cursor, caller=None, direction=Direction.LEFT):
        if not self.has_cursor:
            self.handle_cursor(cursor, direction)
        if direction is Direction.LEFT:
            shift = -1
        elif direction is Direction.RIGHT:
            shift = 0
        if self.cursor_pos + shift in range(len(self.elements)):
            target = self.elements[self.cursor_pos + shift]
            if target.wants_cursor:
                target.handle_cursor(cursor, direction, self)
                target.backspace(cursor, self, direction=direction)
            else:
                self.cursor_pos += shift
                del self.elements[self.cursor_pos]
        elif self.parent:
            self.parent.backspace(cursor, self, direction=direction)

    def replace(self, old, new, cursor_offset=None):
        if old.parent is self:
            if isinstance(new, ElementList):
                self.elements[old.index_in_parent:old.index_in_parent+1] = new.elements
                for i, e in enumerate(new.elements):
                    e.parent = self
                    e.index_in_parent = old.index_in_parent + i
                if self.has_cursor and cursor_offset is not None:
                    self.cursor_pos = old.index_in_parent + cursor_offset
            else:
                self.elements[old.index_in_parent] = new
                new.parent = self

    def insert(self, element, cursor):
        self.elements.insert(self.cursor_pos, element)
        self.cursor_pos += 1
        element.parent = self
        self.convert_specials(cursor)

    def greedy_insert(self, cls, cursor):
        if self.cursor_pos > 0 and cls.greedy_insert_left and isinstance(self.elements[self.cursor_pos-1], (Paren, Atom, Expt)):
            paren_level = 0
            for n, e in enumerate(self.elements[self.cursor_pos-1::-1]):
                if isinstance(e, Paren):
                    if e.left:
                        paren_level -= 1
                    else:
                        paren_level += 1
                if isinstance(e, Expt):
                    continue
                if paren_level <= 0:
                    break
            if paren_level < 0:
                left = []
            else:
                n += 1
                left = self.elements[self.cursor_pos - n:self.cursor_pos]
                del self.elements[self.cursor_pos - n:self.cursor_pos]
                self.cursor_pos -= n
        else:
            left = []
        if self.cursor_pos < len(self.elements) and cls.greedy_insert_right and isinstance(self.elements[self.cursor_pos], (Paren, Atom, Expt)):
            paren_level = 0
            for n, e in enumerate(self.elements[self.cursor_pos:]):
                if isinstance(e, Paren):
                    if e.left:
                        paren_level += 1
                    else:
                        paren_level -= 1
                if isinstance(e, Expt):
                    continue
                if paren_level <= 0:
                    break
            if paren_level < 0:
                right = []
            else:
                n += 1
                right = self.elements[self.cursor_pos:self.cursor_pos + n]
                del self.elements[self.cursor_pos:self.cursor_pos + n]
        else:
            right = []
        new = cls.make_greedily(left, right)
        self.insert(new, cursor)
        new.handle_cursor(cursor, Direction.LEFT)

    def atoms_at_cursor(self):
        l = self.cursor_pos
        while l - 1 >= 0:
            if isinstance(self.elements[l-1], BaseAtom):
                l -= 1
            else:
                break
        r = self.cursor_pos
        while r < len(self.elements):
            if isinstance(self.elements[r], BaseAtom):
                r += 1
            else:
                break
        return l, r

    @staticmethod
    def atoms_to_string(atoms):
        return "".join(deitalify_string(atom.name) for atom in atoms)

    def convert_specials(self, cursor):
        l, r = self.atoms_at_cursor()
        atoms = self.elements[l:r]
        names = string_to_names(self.atoms_to_string(atoms))

        # find index of first difference - it will be stored in i
        for i, name, atom in zip(count(), names, atoms):
            if name != deitalify_string(atom.name):
                break
        else:
            return

        new_elems = [name_to_element(name) for name in names]
        self.elements[l:r] = new_elems
        for j, elem in enumerate(new_elems):
            elem.parent = self
            elem.index_in_parent = l + j
        new_elems[i].handle_cursor(cursor, Direction.RIGHT)

def string_to_names(string):
    regex = r"asinh|acosh|atanh|sinh|cosh|tanh|asin|acos|atan|sin|cos|tan|exp|log|ln|lg|sqrt|."
    regex = "|".join(GREEK_REGEXES) + "|" + regex
    names = re.findall(regex, string)
    return names

def name_to_element(name):
    if name == 'sqrt':
        return Radical([])
    elif len(name) == 1:
        return Atom(name)
    elif name in GREEK_LETTERS:
        return Atom(GREEK_LETTERS[name])
    else:
        return OperatorAtom(name)

class Text:
    def __init__(self, text, ctx):
        self.layout = PangoCairo.create_layout(ctx)
        self.layout.set_text(text)
        self.layout.set_font_description(desc)
        self.width, self.height = self.layout.get_pixel_size()
        self.ascent = self.layout.get_baseline()/Pango.SCALE
        self.descent = self.height - self.ascent

    def draw(self, ctx):
        ctx.move_to(0, -self.ascent)
        PangoCairo.show_layout(ctx, self.layout)
        ctx.move_to(0, 0)

class BaseAtom(Element):
    wants_cursor = False
    h_spacing = 0

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name

    def compute_metrics(self, ctx, metric_ctx):
        self.layout = Text(self.name, ctx)
        self.width, self.ascent, self.descent = self.layout.width, self.layout.ascent, self.layout.descent
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor):
        super().draw(ctx, cursor)
        self.layout.draw(ctx)

class Atom(BaseAtom):
    def __init__(self, name, parent=None):
        super().__init__(italify_string(name), parent=parent)

    def __repr__(self):
        return "Atom({!r})".format(self.name)

class BinaryOperatorAtom(BaseAtom):
    def __init__(self, name, parent=None):
        super().__init__(name, parent=parent)
        if name == "=":
            self.h_spacing = 6
        else:
            self.h_spacing = 4

class OperatorAtom(BaseAtom):
    h_spacing = 2

    @classmethod
    def any_in_string(cls, string):
        for name in cls.allowed_names:
            i = string.find(name)
            if i != -1:
                return name, i

class Expt(Element):
    greedy_insert_right = True
    greedy_insert_left = False
    h_spacing = 0
    exponent_scale = 0.7

    def __init__(self, exponent=None, parent=None):
        super().__init__(parent)
        self.exponent = ElementList(exponent, self)

    def compute_metrics(self, ctx, metric_ctx):
        self.exponent.compute_metrics(ctx, metric_ctx)
        self.child_shift = -self.exponent.descent*self.exponent_scale - metric_ctx.prev.ascent + 14 # -ve y is up
        self.width = self.exponent.width*self.exponent_scale
        self.ascent = self.exponent.ascent*self.exponent_scale - self.child_shift
        self.descent = max(0, metric_ctx.prev.descent,
                           self.exponent.descent*self.exponent_scale + self.child_shift)
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor):
        super().draw(ctx, cursor)
        with saved(ctx):
            ctx.translate(0, self.child_shift)
            ctx.scale(self.exponent_scale, self.exponent_scale)
            self.exponent.draw(ctx, cursor)

    def handle_cursor(self, cursor, direction, giver=None):
        if giver is self.exponent:
            self.parent.handle_cursor(cursor, direction, self)
        else:
            self.exponent.handle_cursor(cursor, direction)

    def backspace(self, cursor, caller, direction=Direction.LEFT):
        if self.parent and caller is self.exponent:
            self.parent.handle_cursor(cursor, Direction.NONE)
            self.parent.replace(self, self.exponent, cursor_offset=0 if direction == Direction.LEFT else len(self.exponent.elements))
        elif caller is self.parent is not None:
            self.exponent.backspace(cursor, self, direction=direction)

    @classmethod
    def make_greedily(cls, left, right):
        return cls(exponent=right)

class Frac(Element):
    vertical_separation = 4
    greedy_insert_right = greedy_insert_left = True

    def __init__(self, numerator=None, denominator=None, parent=None):
        super().__init__(parent)
        self.numerator = ElementList(numerator, self)
        self.denominator = ElementList(denominator, self)

    def compute_metrics(self, ctx, metric_ctx):
        self.numerator.compute_metrics(ctx, metric_ctx)
        self.denominator.compute_metrics(ctx, metric_ctx)
        self.width = max(self.numerator.width, self.denominator.width)

        font_ascent = self.font_metrics(ctx).ascent
        self.bar_height = font_ascent * 0.3
        self.ascent = self.numerator.ascent + self.numerator.descent + \
            self.bar_height + self.vertical_separation//2
        self.descent = self.denominator.ascent + self.denominator.descent + \
            self.vertical_separation//2 - self.bar_height
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor):
        super().draw(ctx, cursor)
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
                self.numerator.draw(ctx, cursor)
            with saved(ctx):
                ctx.translate(self.width//2 - self.denominator.width//2,
                              self.vertical_separation//2 + self.denominator.ascent)
                self.denominator.draw(ctx, cursor)

    def handle_cursor(self, cursor, direction, giver=None):
        if giver is self.numerator and direction is Direction.DOWN:
            self.denominator.handle_cursor(cursor, direction)
        elif giver is self.denominator and direction is Direction.UP:
            self.numerator.handle_cursor(cursor, direction)
        elif giver is self.numerator or giver is self.denominator:
            self.parent.handle_cursor(cursor, direction, self)
        else:
            if direction is Direction.UP or self.numerator.elements and not self.denominator.elements:
                self.denominator.handle_cursor(cursor, direction)
            else:
                self.numerator.handle_cursor(cursor, direction)

    def backspace(self, cursor, caller, direction=Direction.LEFT):
        if self.parent and (caller is self.numerator or caller is self.denominator):
            temp = ElementList(self.numerator.elements + self.denominator.elements)
            self.parent.handle_cursor(cursor, Direction.NONE)
            if direction is Direction.LEFT and caller is self.numerator:
                offset = 0
            elif direction is Direction.LEFT and caller is self.denominator \
                 or direction is Direction.RIGHT and caller is self.numerator:
                offset = len(self.numerator)
            else:
                offset = len(self.numerator) + len(self.denominator)
            self.parent.replace(self, temp, cursor_offset=offset)
        elif caller is self.parent is not None:
            self.denominator.backspace(cursor, self, direction=direction)

    @classmethod
    def make_greedily(cls, left, right):
        return cls(numerator=left, denominator=right)

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

    def draw(self, ctx, cursor):
        super().draw(ctx, cursor)
        extents = self.symbol.get_pixel_extents()
        symbol_size = extents.ink_rect.height
        scale_factor = max(1, (self.ascent + self.descent)/symbol_size)
        with saved(ctx):
            ctx.translate(0, -self.ascent)
            ctx.scale(1, scale_factor)
            ctx.translate(0, -extents.ink_rect.y)
            ctx.move_to(0, 0)
            PangoCairo.show_layout(ctx, self.symbol)

        ctx.translate(self.symbol.get_pixel_size().width, 0)
        ctx.set_source_rgb(0,0,0)
        ctx.set_line_width(1)
        ctx.move_to(0, -self.ascent + ctx.get_line_width())
        ctx.rel_line_to(self.radicand.width, 0)
        ctx.stroke()
        ctx.move_to(0,0)
        self.radicand.draw(ctx, cursor)

    def handle_cursor(self, cursor, direction, giver=None):
        if giver is self.radicand:
            self.parent_handle_cursor(cursor, direction)
        else:
            self.radicand.handle_cursor(cursor, direction)

    def backspace(self, cursor, caller, direction=Direction.LEFT):
        if caller is self.radicand and self.parent:
            self.parent_handle_cursor(cursor, Direction.NONE)
            self.parent.replace(self, self.radicand, cursor_offset=0 if direction is Direction.LEFT else len(self.radicand))
        elif caller is self.parent is not None:
            self.radicand.backspace(cursor, self, direction=direction)

class Paren(Element):
    wants_cursor = False
    h_spacing = 0

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
            if metric_ctx.paren_stack:
                match = metric_ctx.paren_stack.pop()
            else:
                match = metric_ctx.prev
            self.ascent = match.ascent
            self.descent = match.descent
            super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor):
        super().draw(ctx, cursor)
        extents = self.layout.get_pixel_extents()
        symbol_size = extents.ink_rect.height
        scale_factor = max(1, (self.ascent + self.descent)/symbol_size)
        with saved(ctx):
            ctx.scale(1, scale_factor)
            ctx.translate(0, -self.ascent/scale_factor-extents.ink_rect.y)
            ctx.move_to(0, 0)
            PangoCairo.show_layout(ctx, self.layout)
