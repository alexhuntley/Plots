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

from locale import gettext as _
import locale
import importlib.resources as resources

domain = "plots"
localedir = resources.path("plots.locale", "__init__.py").__enter__().parent
locale.setlocale(locale.LC_ALL, "")
locale.bindtextdomain(domain, localedir)
locale.textdomain(domain)
