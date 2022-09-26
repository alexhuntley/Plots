from . import element
from plots.utils import saved, italify_string, deitalify_string, Text
from plots.data import GREEK_LETTERS_INVERSE

class BaseAtom(element.Element):
    h_spacing = 0

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name

    def compute_metrics(self, ctx, metric_ctx):
        self.layout = Text(self.name, ctx)
        self.width, self.ascent, self.descent = self.layout.width, self.layout.ascent, self.layout.descent
        super().compute_metrics(ctx, metric_ctx)

    def draw(self, ctx, cursor, widget_transform):
        super().draw(ctx, cursor, widget_transform)
        self.layout.draw_at_baseline(ctx)

    def __repr__(self):
        return "{}({!r})".format(type(self).__name__, self.name)

    def __eq__(self, other):
        if isinstance(other, BaseAtom):
            return self.name == other.name
        return NotImplemented

    def to_glsl(self):
        s = deitalify_string(self.name)
        if s in GREEK_LETTERS_INVERSE:
            return "", GREEK_LETTERS_INVERSE[s]
        else:
            return "", deitalify_string(self.name)

    def to_latex(self):
        return deitalify_string(self.name)

class Atom(BaseAtom):
    def __init__(self, name, parent=None):
        super().__init__(italify_string(name), parent=parent)

    @staticmethod
    def part_of_number(element):
        return isinstance(element, Atom) \
            and (element.name.isdigit() or element.name == ".")

class BinaryOperatorAtom(BaseAtom):
    def __init__(self, name, parent=None):
        super().__init__(name, parent=parent)
        if name == "=":
            self.h_spacing = 6
        else:
            self.h_spacing = 4

    def to_glsl(self):
        translation = str.maketrans("−×", "-*")
        return "", self.name.translate(translation)

    def to_latex(self):
        if self.name == "−":
            return "-"
        elif self.name == "×":
            return "\\times "
        else:
            return self.name

class OperatorAtom(BaseAtom):
    h_spacing = 2

    def to_latex(self):
        return "\\operatorname{" + self.name + "}"
