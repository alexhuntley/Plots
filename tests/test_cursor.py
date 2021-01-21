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

from plots.cursor import Cursor
import plots.formula as f
from plots.parser import from_latex
from plots.utils import Direction

def test_position_changed():
    cursor = Cursor()
    assert cursor.position_changed == False
    cursor.position = (1., 1.)
    assert cursor.position_changed == True

def test_position_not_changed():
    cursor = Cursor()
    assert cursor.position_changed == False
    cursor.position = (0., 0.)
    assert cursor.position_changed == False

def test_select_all_backspace():
    cursor = Cursor()
    elems = from_latex("abcd")
    cursor.reparent(elems, 2)
    cursor.select_all(elems)
    cursor.backspace(None)
    assert len(elems) == 0

def test_backspace():
    cursor = Cursor()
    elems = from_latex("abcd")
    cursor.reparent(elems, 2)
    cursor.backspace(Direction.LEFT)
    assert elems.to_latex() == "acd"
