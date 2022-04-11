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
from gi.repository import Gtk

import importlib.resources as resources

from plots.i18n import _
import plots.i18n

def read_ui_file(name):
    return resources.read_text("plots.ui", name)

class Preferences:
    def __init__(self, parent):
        self.parent = parent

    def show(self):
        self.window = PreferencesWindow(self.parent)
        self.window.show()

class PreferencesWindow:
    def __init__(self, parent):
        builder = Gtk.Builder()
        builder.add_from_string(read_ui_file("preferences.glade"))
        builder.set_translation_domain(plots.i18n.domain)
        builder.connect_signals(self)

        self.prefs_window = builder.get_object("prefs_window")
        self.prefs_window.set_transient_for(parent)
        self.prefs_window.props.modal = True

    def show(self):
        self.prefs_window.show()
