import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import formula
import converters

class Calcula:
    def on_destroy(self, *args):
        Gtk.main_quit()

    def key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            expr = converters.elementlist_to_sympy(self.formulae[-1].expr)
            answer_display = formula.Editor(converters.sympy_to_elementlist(expr))
            self.add_formula_editor(answer_display)
            self.add_formula_editor(formula.Editor())

    def add_formula_editor(self, editor):
        self.formulae.append(editor)
        self.formula_box.pack_start(editor, False, False, 0)
        editor.show_all()
        editor.grab_focus()

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
