#!/usr/bin/env python3

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

from gi.repository import Gtk, Adw, GObject

import copy
import os
import configparser

import plots.i18n
from plots import utils

def xdg_config_home():
    varname = "XDG_CONFIG_HOME"
    if varname in os.environ:
        return os.environ[varname]
    else:
        return "{}/.config".format(os.environ["HOME"])


class Preferences(GObject.GObject):
    __gsignals__ = {
        "updated": (GObject.SIGNAL_RUN_FIRST, None, ())
    }
    DEFAULTS = {
        "rendering": {
            "line_thickness": 2.0,
            "samples": 32,
            "grid_opacity": .5,
        }
    }
    CONFIG_DIR = "plots"
    CONFIG_FILENAME = "config.ini"

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.data = copy.deepcopy(self.DEFAULTS)
        self.load_config()

    def load_config(self):
        filename = f"{xdg_config_home()}/{self.CONFIG_DIR}/{self.CONFIG_FILENAME}"
        config = configparser.ConfigParser()
        config.read(filename)
        for sec in self.data.keys() & config.keys():
            datasec = self.data[sec]
            for option in datasec.keys() & config[sec].keys():
                if option in datasec:
                    t = type(datasec[option])
                    datasec[option] = t(config[sec][option])

    def save_config(self):
        conf_dir = f"{xdg_config_home()}/{self.CONFIG_DIR}"
        os.makedirs(conf_dir, exist_ok=True)
        filename = f"{conf_dir}/{self.CONFIG_FILENAME}"
        config = configparser.ConfigParser()
        config.read_dict(self.data)
        with open(filename, "w") as f:
            config.write(f)

    def show(self):
        self.window = PreferencesWindow(self, self.parent)
        self.window.connect("close-request", self.close_cb)
        self.window.show()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def close_cb(self, prefs_window):
        self.emit("updated")
        return False


@Gtk.Template(string=utils.read_ui_file("preferences.ui"))
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    line_thickness_scale = Gtk.Template.Child()
    samples_scale = Gtk.Template.Child()
    grid_opacity = Gtk.Template.Child()

    def __init__(self, prefs, parent_window):
        super().__init__()
        self.prefs = prefs

        self.set_transient_for(parent_window)
        self.props.modal = True
        self.connect("close-request", self.delete_cb)

        self.line_thickness_scale.set_range(1, 10)
        self.line_thickness_scale.set_increments(0.5, 3)
        self.line_thickness_scale.set_value(prefs["rendering"]["line_thickness"])

        self.samples_scale.set_range(4, 128)
        self.samples_scale.set_value(prefs["rendering"]["samples"])
        self.samples_scale.set_digits(0)
        self.samples_scale.set_increments(1, 10)

        self.grid_opacity.set_range(0, 1)
        self.grid_opacity.set_value(prefs["rendering"]["grid_opacity"])
        self.grid_opacity.set_increments(0.5, 3)

    def delete_cb(self, window):
        r = self.prefs["rendering"]
        r["line_thickness"] = self.line_thickness_scale.get_value()
        r["samples"] = int(self.samples_scale.get_value())
        r["grid_opacity"] = self.grid_opacity.get_value()
