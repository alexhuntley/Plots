from . import elements
from . import element
from plots.utils import saved, Text

class Paren(element.Element):
    h_spacing = 0
    shrink = 0.7

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
        self.match = None

    def __repr__(self):
        return f'Paren({self.char!r})'

    def compute_metrics(self, ctx, metric_ctx):
        self.text = Text(self.char, ctx)
        if self.char == "[":
            self.top, self.mid, self.bot = [Text(c, ctx) for c in "⎡⎢⎣"]
        elif self.char == "]":
            self.top, self.mid, self.bot = [Text(c, ctx) for c in "⎤⎥⎦"]

        self.width, self.ascent, self.descent = self.text.width, self.text.ascent, self.text.descent

        if self.left:
            metric_ctx.paren_stack.append(self)
        else:
            if metric_ctx.paren_stack:
                self.match = metric_ctx.paren_stack.pop()
            else:
                self.match = metric_ctx.prev
            self.ascent = self.match.ascent
            self.descent = self.match.descent
            super().compute_metrics(ctx, metric_ctx)
        self.compute_stretch()

    def compute_stretch(self):
        self.scale_factor = max(1, (self.ascent + self.descent)/self.text.ink_rect.height)
        if self.scale_factor > 1.5 and self.char in "[]":
            self.stretch = True
            self.scale_factor = max(1, (self.ascent + self.descent)/self.mid.height)
            self.width = self.mid.width*self.shrink
            self.h_spacing = 0
            if isinstance(self.match, Paren) and self.match.char in "[]":
                self.match.stretch = True
                self.match.scale_factor = self.scale_factor
                self.match.width = self.width
                self.match.h_spacing = self.h_spacing
        else:
            self.stretch = False

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        if self.stretch:
            with saved(ctx):
                ctx.translate(0, -self.ascent - self.top.ink_rect.y*self.shrink)
                ctx.move_to(0,0)
                ctx.scale(self.shrink,self.shrink)
                self.top.draw(ctx)
            with saved(ctx):
                ctx.translate(0, self.descent)
                ctx.move_to(0,0)
                ctx.scale(self.shrink,self.shrink)
                ctx.translate(0, -self.bot.ink_rect.y - self.bot.ink_rect.height)
                ctx.move_to(0,0)
                self.bot.draw(ctx)
            with saved(ctx):
                scale_factor = max(1, (self.ascent + self.descent)/self.mid.ink_rect.height)
                ctx.translate(0, -self.ascent)
                ctx.scale(1, self.scale_factor)
                ctx.translate(0, -self.mid.ink_rect.y)
                ctx.scale(self.shrink,1)
                ctx.move_to(0, 0)
                self.mid.draw(ctx)
        else:
            with saved(ctx):
                ctx.scale(1, self.scale_factor)
                ctx.translate(0, -self.ascent/self.scale_factor-self.text.ink_rect.y)
                ctx.move_to(0, 0)
                self.text.draw(ctx)

    def to_glsl(self):
        return "", "(" if self.left else ")"

    def to_latex(self):
        if self.char in "{}":
            return "\\" + self.char
        else:
            return self.char

    @classmethod
    def is_paren(cls, element, left=None):
        if not isinstance(element, cls):
            return False
        if left is None:
            return True
        return left == element.left
