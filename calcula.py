import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import formula

class Calcula:
    def on_destroy(self, *args):
        Gtk.main_quit()

    def key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            self.add_formula_editor(formula.Editor())

    def add_formula_editor(self, editor):
        self.formulae.append(editor)
        self.formula_box.pack_start(editor, False, False, 0)
        editor.show_all()

    def main(self):
        builder = Gtk.Builder()
        builder.add_from_file("calcula.glade")
        builder.connect_signals(self)

        self.window = builder.get_object("main_window")

        self.formula_box = builder.get_object("calculationbox")
        for c in self.formula_box.get_children():
            self.formula_box.remove(c)

        self.formulae = [formula.Editor()]
        self.formula_box.pack_start(self.formulae[0], False, False, 0)

        self.window.show_all()

        Gtk.main()

if __name__ == '__main__':
    Calcula().main()
