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

lefts = [f.Paren(c) for c in "([{"]
rights = [f.Paren(c) for c in "}])"]

@pytest.mark.parametrize("paren", lefts + rights)
def test_is_paren(paren):
    assert f.Paren.is_paren(paren)

def test_is_not_paren():
    assert not f.Paren.is_paren(f.Atom("f"))

@pytest.mark.parametrize("paren", lefts)
def test_is_left_paren(paren):
    assert f.Paren.is_paren(paren, left=True)

@pytest.mark.parametrize("paren", rights)
def test_is_not_left_paren(paren):
    assert not f.Paren.is_paren(paren, left=True)

@pytest.mark.parametrize("paren", rights)
def test_is_right_paren(paren):
    assert f.Paren.is_paren(paren, left=False)

@pytest.mark.parametrize("paren", lefts)
def test_is_not_right_paren(paren):
    assert not f.Paren.is_paren(paren, left=False)
