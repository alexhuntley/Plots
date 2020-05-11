import gi
gi.require_version('PangoCairo', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, cairo, Pango, PangoCairo
import math
import sys

from formula import *

test_expr = ElementList([Paren('('), Atom('a'), Paren(')'), Atom('b'), Atom('c'), Expt([Atom('dasdlaksjdkl')]),
                         Paren('('),
                         Frac([Radical([Frac([Atom('b')], [Atom('c')]), Atom('y')], [Atom('3')])], [Atom('cab'), Radical([Atom('ab')])]),
                         Paren(')')])

class Editor(Gtk.DrawingArea):
    def __init__ (self):
        super().__init__()

    def do_draw_cb(self, widget, ctx):
        scale = 2
        ctx.scale(scale, scale)
        test_expr.compute_metrics(ctx)
        ctx.translate(0, test_expr.ascent)
        test_expr.draw(ctx)
        self.set_size_request(test_expr.width*scale,
                              (test_expr.ascent + test_expr.descent)*scale)


def destroy(window):
    Gtk.main_quit()

def main():
    window = Gtk.Window()
    window.set_title("Hello World")

    app = Editor()

    window.add(app)

    app.connect('draw', app.do_draw_cb)
    window.connect_after('destroy', destroy)
    window.show_all()
    Gtk.main()

if __name__ == "__main__":
    sys.exit(main())
