import gi
gi.require_version('PangoCairo', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, cairo, Pango, PangoCairo
import math
import sys

from . import formula

def destroy(window):
    Gtk.main_quit()

def main():
    window = Gtk.Window()
    window.set_title("Formula Editor")

    editor = formula.Editor()
    window.add(editor)

    window.connect_after('destroy', destroy)
    window.show_all()

    Gtk.main()

if __name__ == "__main__":
    sys.exit(main())
