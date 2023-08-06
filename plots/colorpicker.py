# Copyright 2021-2022 Alexander Huntley

# This file is part of Plots.

# Plots is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Plots is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Plots.  If not, see <https://www.gnu.org/licenses/>.

import gi
from gi.repository import Gtk, GObject, Gdk
from plots.i18n import _

class PopoverColorPicker(Gtk.Button):
    __gtype_name__ = "PopoverColorPicker"
    __gsignals__ = {
        "color-activated": (GObject.SIGNAL_RUN_FIRST, None,
                            (Gtk.ColorChooser, Gdk.RGBA))
    }

    def __init__(self):
        super().__init__()

        self.set_tooltip_text(_("Pick a color"))

        self.chooser = Gtk.ColorChooserWidget.new()
        self.chooser.show()
        self.chooser.connect("color-activated", self.on_color_activated)
        click_ctl = Gtk.GestureClick()
        click_ctl.connect("pressed", self.on_button)
        self.chooser.add_controller(click_ctl)

        self.popover = Gtk.Popover()
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        self.popover.set_parent(self)
        self.popover.set_child(self.chooser)
        self.popover.connect("closed", self.on_close)

        self.connect("clicked", self.on_click)

        self.provider = Gtk.CssProvider()
        context = self.get_style_context()
        context.add_provider(self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.update_color()


    def update_color(self):
        css = f'button {{ background: {self.get_rgba().to_string()}; }}'
        self.provider.load_from_data(css, len(css))

    def on_click(self, button):
        self.chooser.props.show_editor = False
        self.popover.popup()

    def on_close(self, popover):
        self.on_color_activated(self.chooser, self.get_rgba())

    def get_rgba(self):
        return self.chooser.get_rgba()

    def set_rgba(self, color):
        self.chooser.set_rgba(color)
        self.update_color()

    def add_palette(self, orientation, colors_per_line, colors):
        self.chooser.add_palette(orientation, colors_per_line, colors)

    def on_color_activated(self, chooser, color):
        self.emit("color-activated", chooser, color)
        self.set_rgba(color)

    def on_button(self, ctl, n_press, x, y):
        self.on_color_activated(self.chooser, self.get_rgba())
