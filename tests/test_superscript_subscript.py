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

from plots.parser import from_latex
from plots.utils import Direction
import plots.formula as f

from tests.fixtures import cursor

def test_insert_empty_super(cursor):
    elems = from_latex("x")
    cursor.reparent(elems, -1)
    cursor.insert_superscript_subscript()
    assert elems.to_latex() == r"x^{}"
    assert cursor.owner is elems[1].exponent

def test_add_to_super_after(cursor):
    elems = from_latex("x^{2}2")
    cursor.reparent(elems, -1)
    cursor.handle_movement(Direction.LEFT, select=True)
    cursor.insert_superscript_subscript()
    assert elems.to_latex() == "x^{22}"
    assert cursor.owner is elems[1].exponent

def test_add_to_super_after_alternative(cursor):
    elems = from_latex("x^{2}2")
    cursor.reparent(elems, 2)
    cursor.handle_movement(Direction.RIGHT, select=True)
    cursor.insert_superscript_subscript()
    assert elems.to_latex() == "x^{22}"
    assert cursor.owner is elems[1].exponent

def test_add_to_super_before(cursor):
    elems = from_latex("xy^{z}")
    cursor.reparent(elems, 1)
    cursor.handle_movement(Direction.RIGHT, select=True)
    cursor.insert_superscript_subscript()
    assert elems.to_latex() == "x^{yz}"
    assert cursor.owner is elems[1].exponent

def test_add_to_super_before_alternative(cursor):
    elems = from_latex("xy^{z}")
    cursor.reparent(elems, 2)
    cursor.handle_movement(Direction.LEFT, select=True)
    cursor.insert_superscript_subscript()
    assert elems.to_latex() == "x^{yz}"
    assert cursor.owner is elems[1].exponent

def test_move_to_super_before(cursor):
    elems = from_latex("x^{2}")
    cursor.reparent(elems, 1)
    cursor.insert_superscript_subscript()
    assert elems.to_latex() == "x^{2}"
    assert cursor.owner is elems[1].exponent

def test_delete_super(cursor):
    elems = from_latex("x_{4}^{3}")
    cursor.reparent(elems[1].exponent, 0)
    cursor.backspace(Direction.LEFT)
    assert elems.to_latex() == "x_{4}3"

def test_delete_sub(cursor):
    elems = from_latex("x_{4}^{3}")
    cursor.reparent(elems[1].subscript, 0)
    cursor.backspace(Direction.LEFT)
    assert elems.to_latex() == "x4^{3}"

def test_add_sub_to_super(cursor):
    elems = from_latex("x^{3}")
    cursor.reparent(elems, -1)
    cursor.insert_superscript_subscript(superscript=False)
    assert elems.to_latex() == "x_{}^{3}"
    assert cursor.owner is elems[1].subscript

def test_add_super_to_sub(cursor):
    elems = from_latex("x_{3}")
    cursor.reparent(elems, -1)
    cursor.insert_superscript_subscript(superscript=True)
    assert elems.to_latex() == "x_{3}^{}"
    assert cursor.owner is elems[1].exponent
