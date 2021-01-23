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

from tests.fixtures import cursor

import pytest

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

def test_move_to_next_list(cursor):
    elems = from_latex(r"\frac{3}{2}")
    cursor.reparent(elems[0].numerator, -1)
    cursor.handle_movement(Direction.RIGHT)
    assert cursor.owner is elems[0].denominator
    assert cursor.pos == 0

def test_move_to_previous_list(cursor):
    elems = from_latex(r"\frac{3}{2}")
    cursor.reparent(elems[0].denominator, 0)
    cursor.handle_movement(Direction.LEFT)
    assert cursor.owner is elems[0].numerator
    assert cursor.pos == 1

def test_ancestors(cursor):
    elems = from_latex(r"\sqrt{\operatorname{cos}\frac{3}{4\abs{\sum_{i=1}^{3}}}}")
    expected = [
        elems[0].radicand[1].denominator[1].argument[0].bottom,
        elems[0].radicand[1].denominator[1].argument,
        elems[0].radicand[1].denominator,
        elems[0].radicand,
        elems,
    ]
    actual = cursor.ancestors(elems[0].radicand[1].denominator[1].argument[0].bottom)
    for e, a in zip(expected, actual):
        assert e is a

def test_calculate_selection_deep(cursor):
    elems = from_latex(r"x\abs{3}-3\sqrt{\frac{2}{x}}+4")
    cursor.reparent(elems[1].argument, -1)
    cursor.secondary_owner = elems[4].radicand[0].denominator
    cursor.secondary_pos = 0
    _range, ancestor = cursor.calculate_selection()
    assert _range == range(1, 5)
    assert ancestor is elems

def test_calculate_selection_deep_alternative(cursor):
    elems = from_latex(r"x\abs{3}-3\sqrt{\frac{2}{x}}+4")
    cursor.reparent(elems[4].radicand[0].denominator, -1)
    cursor.secondary_owner = elems[1].argument
    cursor.secondary_pos = 0
    _range, ancestor = cursor.calculate_selection()
    assert _range == range(1, 5)
    assert ancestor is elems

def test_mouse_select_drag_deep(cursor):
    elems = from_latex(r"x\abs{3}-3\sqrt{\frac{2}{x}}+4")
    cursor.reparent(elems[4].radicand[0].denominator, -1)
    cursor.mouse_select(elems[1].argument[0], Direction.LEFT, drag=True)
    assert cursor.selection_bounds == range(1, 5)
    assert cursor.selection_ancestor == elems

def test_mouse_select_left(cursor):
    elems = from_latex(r"abcd")
    cursor.mouse_select(elems[1], Direction.LEFT, drag=False)
    assert cursor.owner is elems
    assert cursor.pos is 1

def test_mouse_select_right(cursor):
    elems = from_latex(r"abcd")
    cursor.mouse_select(elems[1], Direction.RIGHT, drag=False)
    assert cursor.owner is elems
    assert cursor.pos is 2

def test_mouse_select_list(cursor):
    elems = from_latex(r"3x\abs{}")
    cursor.mouse_select(elems[2].argument, Direction.RIGHT, drag=False)
    assert cursor.owner is elems[2].argument
    assert cursor.pos is 0

def test_mouse_select_then_drag(cursor):
    elems = from_latex(r"abcd")
    cursor.mouse_select(elems[1], Direction.LEFT, drag=False)
    cursor.mouse_select(elems[3], Direction.LEFT, drag=True)
    assert cursor.owner is elems
    assert cursor.selection_bounds == range(1, 3)

def test_handle_movement_up_out(cursor):
    elems = from_latex(r"\abs{x}")
    cursor.reparent(elems[0].argument, -1)
    cursor.handle_movement(Direction.UP)
    assert cursor.owner is elems
    assert cursor.pos == 0

def test_handle_movement_down_out(cursor):
    elems = from_latex(r"\abs{x}")
    cursor.reparent(elems[0].argument, -1)
    cursor.handle_movement(Direction.DOWN)
    assert cursor.owner is elems
    assert cursor.pos == 1
