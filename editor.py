import gi
gi.require_version('PangoCairo', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, cairo, Pango, PangoCairo
import math
import sys

from formula import *

def destroy(window):
    Gtk.main_quit()

def main():
    window = Gtk.Window()
    window.set_title("Hello World")
    window.set_events(window.get_events() | Gdk.EventMask.KEY_PRESS_MASK)

    app = Editor()

    window.add(app)

    app.connect('draw', app.do_draw_cb)
    window.connect_after('destroy', destroy)
    window.show_all()
    Gtk.main()

if __name__ == "__main__":
    sys.exit(main())
