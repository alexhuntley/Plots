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

import plots.formula as f
from plots.parser import from_latex
from plots.cursor import Cursor
import plots.data
import plots.utils

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
    assert isinstance(elem, f.OperatorAtom) and elem.name == fn

@pytest.mark.parametrize("name, symbol", [tup for tup in plots.data.GREEK_LETTERS.items()])
def test_convert_specials_greek(name, symbol):
    elems = do_convert_specials(name)
    assert len(elems) == 1
    elem = elems[0]
    assert isinstance(elem, f.Atom) \
        and plots.utils.deitalify_string(elem.name) == symbol

@pytest.mark.parametrize("name", "epsi upsi".split())
def test_convert_specials_epsilon_upsilon(name):
    elems = do_convert_specials(name)
    assert len(elems) == len(name)
    assert elems.to_latex() == name

@pytest.mark.parametrize("name, cls", [
    ("sum", f.Sum),
    ("prod", f.Sum),
    ("sqrt", f.Radical),
    ("nthroot", f.Radical),
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
