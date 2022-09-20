import gi
from gi.repository import GLib, Gtk, Gdk

from plots.utils import saved, Direction

from . import elements
from . import abstractelement

DEBUG = False

class Element(abstractelement.AbstractElement):
    """Abstract class describing an element of an equation.

    Implementations must provide parent, index_in_parent, lists, ascent, descent,
    and width properties, compute_metrics(ctx, metric_ctx) and draw(ctx, cursor, widget_transform)."""

    h_spacing = 2
    color = Gdk.RGBA()

    def __init__(self, parent):
        super().__init__(parent)
        self.index_in_parent = None
        self.lists = []
        self.default_list = None
        self.cursor_acceptor = None

    def children(self):
        return self.lists

    def compute_metrics(self, ctx, metric_ctx):
        """To be run at the end of overriding methods, if they
        wish to have parens scale around them.
        """
        stack = metric_ctx.paren_stack
        if stack:
            stack[-1].ascent = max(self.ascent, stack[-1].ascent)
            stack[-1].descent = max(self.descent, stack[-1].descent)
            stack[-1].compute_stretch()

    def draw(self, ctx, cursor, widget_transform):
        """Expects (0, 0) to be at the baseline, where it should begin drawing.
        """
        super().draw(ctx, cursor, widget_transform)
        if DEBUG:
            ctx.set_line_width(0.5)
            ctx.set_source_rgba(1, 0, 1 if cursor.owner is self else 0, 0.6)
            ctx.rectangle(0, -self.ascent, self.width, self.ascent + self.descent)
            ctx.stroke()
        if cursor.selecting and self.parent is cursor.selection_ancestor and \
           self.index_in_parent in cursor.selection_bounds:
            ctx.set_source_rgba(*cursor.selection_rgba)
            ctx.rectangle(-self.h_spacing, -self.ascent,
                          self.width + 2*self.h_spacing, self.ascent + self.descent)
            ctx.fill()
        Gdk.cairo_set_source_rgba(ctx, Element.color)
        ctx.move_to(0, 0)

    def get_next_child(self, direction, previous=None):
        try:
            previous_idx = self.lists.index(previous)
            new_idx = previous_idx + direction.displacement()
            if new_idx in range(len(self.lists)):
                return self.lists[new_idx]
            else:
                return None
        except ValueError:
            child_idx = -1 if direction.displacement() == -1 else 0
            if self.lists:
                return self.lists[child_idx]
            else:
                return None

    def accept_selection(self, elements, direction):
        pass

    def dissolve(self, cursor, caller):
        concatenation = []
        cursor_offset = 0
        for elementlist in self.lists:
            if elementlist is caller:
                cursor_offset = len(concatenation)
            concatenation.extend(elementlist.elements)
        self.parent.replace(self, elements.ElementList(concatenation), cursor, cursor_offset)
