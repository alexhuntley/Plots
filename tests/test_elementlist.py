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

import pytest

import plots.elements as e
from plots.parser import from_latex
from plots.cursor import Cursor
import plots.data
import plots.utils

from tests.fixtures import cursor

def do_convert_specials(name):
    elems = from_latex(name)
    cursor = Cursor()
    cursor.reparent(elems, -1)
    elems.convert_specials(cursor)
    return elems

@pytest.mark.parametrize("fn", plots.data.FUNCTIONS)
def test_convert_specials_functions(fn):
    elems = do_convert_specials(fn)
    assert len(elems) == 1
    elem = elems[0]
    assert isinstance(elem, e.OperatorAtom) and elem.name == fn

@pytest.mark.parametrize("name, symbol", [tup for tup in plots.data.GREEK_LETTERS.items()])
def test_convert_specials_greek(name, symbol):
    elems = do_convert_specials(name)
    assert len(elems) == 1
    elem = elems[0]
    assert isinstance(elem, e.Atom) \
        and plots.utils.deitalify_string(elem.name) == symbol

@pytest.mark.parametrize("name", "epsi upsi".split())
def test_convert_specials_epsilon_upsilon(name):
    elems = do_convert_specials(name)
    assert len(elems) == len(name)
    assert elems.to_latex() == name

@pytest.mark.parametrize("name, cls", [
    ("sum", e.Sum),
    ("prod", e.Sum),
    ("sqrt", e.Radical),
    ("nthroot", e.Radical),
    ("floor", e.Floor),
    ("ceil", e.Ceil),
])
def test_convert_specials_misc(name, cls):
    elems = do_convert_specials(name)
    assert len(elems) == 1
    assert isinstance(elems[0], cls)

@pytest.mark.parametrize("base", "sin cos tan sec cosec csc cot".split())
@pytest.mark.parametrize("template", ["a{}", "arc{}", "{}h", "a{}h"])
def test_convert_specials_add_to_trig(base, template):
    op = f"\\operatorname{{{base}}}"
    elems = do_convert_specials(template.format(op))
    assert len(elems) == 1
    assert elems[0].name == template.format(base)

def test_greedy_insert(cursor):
    elems = from_latex(r"3\sqrt{x}(x(9-x))-4")
    cursor.reparent(elems, 2)
    cursor.greedy_insert(e.Frac)
    assert elems.to_latex() == r"3\frac{\sqrt{x}}{(x(9-x))}-4"

def test_greedy_insert_with_parens(cursor):
    elems = from_latex(r"3(x+1)(x(9-x))-4")
    cursor.reparent(elems, 6)
    cursor.greedy_insert(e.Frac)
    assert elems.to_latex() == r"3\frac{(x+1)}{(x(9-x))}-4"

def test_greedy_insert_with_numbers(cursor):
    elems = from_latex(r"3.238923829-4")
    cursor.reparent(elems, 6)
    cursor.greedy_insert(e.Frac)
    assert elems.to_latex() == r"\frac{3.2389}{23829}-4"

def test_dissolve(cursor):
    elems = from_latex(r"\frac{abc}{def}")
    cursor.reparent(elems[0].numerator, 0)
    cursor.backspace(plots.utils.Direction.LEFT)
    assert elems.to_latex() == "abcdef"
    assert cursor.owner is elems

def test_backspace_into(cursor):
    elems = from_latex(r"\frac{abc}{def}")
    cursor.reparent(elems, -1)
    cursor.backspace(plots.utils.Direction.LEFT)
    assert elems.to_latex() == r"\frac{abc}{de}"
    assert cursor.owner is elems[0].denominator
    assert cursor.pos == 2

def test_delete_into(cursor):
    elems = from_latex(r"\frac{abc}{def}")
    cursor.reparent(elems, 0)
    cursor.backspace(plots.utils.Direction.RIGHT)
    assert elems.to_latex() == r"\frac{bc}{def}"
    assert cursor.owner is elems[0].numerator
    assert cursor.pos == 0

def test_frac_accept_selection(cursor):
    elems = from_latex(r"xyz")
    cursor.select_all(elems)
    cursor.greedy_insert(e.Frac)
    assert elems.to_latex() == r"\frac{xyz}{}"
    assert cursor.owner is elems[0].denominator
