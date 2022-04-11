#!/usr/bin/env python3

# Copyright 2021 Alexander Huntley

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
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf, cairo, Handy

def read_ui_file(name):
    return resources.read_text("plots.ui", name)

def run():
    builder = Gtk.Builder()
    builder.add_from_string(read_ui_file("plots.glade"))
    builder.set_translation_domain(plots.i18n.domain)
    builder.connect_signals(self)

    self.window = builder.get_object("main_window")
    self.add_window(self.window)
