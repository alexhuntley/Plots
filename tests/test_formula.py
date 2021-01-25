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
import plots.parser

@pytest.mark.parametrize("elems, expected", [
    ([e.Atom('x')],
     'x'),
    ([e.Atom('x'), e.Atom('y')],
     'x*y'),
    ([e.Frac([e.Atom('x')], [e.Atom('y')])],
     '(x)/(y)'),
    ([e.Abs([e.Atom('x')])],
     r'abs(x)'),
    ([e.Floor([e.Atom('x')]), e.Atom('y')],
     r'floor(x)*y'),
    ([e.Ceil([e.Atom('x')]), e.SuperscriptSubscript(exponent=e.ElementList([e.Atom('3')]))],
     r'mypow(ceil(x), (3.0))'),
    ([e.Atom('x'), e.SuperscriptSubscript(
        exponent=e.ElementList([e.Atom('2')]))],
     'mypow(x, (2.0))'),
    ([e.Atom('x'), e.Atom('!')],
     'factorial(x)'),
    ([e.OperatorAtom('sin'), e.Atom('x')],
     'sin(x)'),
    ([e.OperatorAtom('sin'), e.Atom('3'), e.Atom('x')],
     'sin(3.0*x)'),
    ([e.OperatorAtom('sin'), e.Paren("{"), e.Atom('3'), e.Atom('x'), e.Paren("}"), e.Atom('y')],
     'sin(3.0*x)*y'),
    ([e.OperatorAtom('sin'), e.Paren("{"), e.Atom('3'), e.Atom('x'), e.Paren("}"),
      e.SuperscriptSubscript(
          exponent=e.ElementList([e.Atom('3'), e.Atom('z')])
      )],
     'mypow(sin(3.0*x), (3.0*z))'),
    ([e.OperatorAtom('sin'), e.Atom('3'), e.BinaryOperatorAtom('-'), e.Atom('x')],
     'sin(3.0)-x'),
    ([e.OperatorAtom('sin'), e.BinaryOperatorAtom('-'), e.Atom('x')],
     'sin(-x)'),
    ([e.Atom('y'), e.Radical([
        e.Atom('x'), e.BinaryOperatorAtom('-'), e.Atom('1')])],
     'y*sqrt(x-1.0)'),
    ([e.Atom('y'), e.Radical([
        e.Atom('x'), e.BinaryOperatorAtom('-'), e.Atom('1')],
                             index=[e.Atom('3')])],
     'y*pow(x-1.0, 1.0/(3.0))'),
])
def test_elementlist_to_glsl(elems, expected):
    assert e.ElementList(elems).to_glsl() == ('', expected)

@pytest.mark.parametrize('string', [
    "x",
    "3x",
    "xyz^{4}",
    r"\operatorname{sin}\frac{3}{x}",
    r"\abs{y^{2}}^{2}",
    r"3\floor{\frac{1}{x}}",
    r"3\ceil{\frac{1}{x}}",
    r"ΑαΒβΓγΔδΕεΖζΗηΘθΙιΚκΛλΜμΝνΞξΟοΠπΡρΣσςΤτΥυΦφΧχΨψΩω",
    "33!",
    r"\operatorname{log}_{10}^{2}(x^{3})",
    r"\sqrt{9x_{a}}",
    r"\sqrt[3-n]{x}",
    r"\sum_{i=1}^{n}[36i^{2}]",
    r"\prod_{a=-5}^{-1}\{abc\}",
    r"-3.2342838^{5}",
    r"+-\times=",
    r"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
])
def test_parse_and_serialize(string):
    assert string == plots.parser.from_latex(string).to_latex()

def test_parse_parent_pointers():
    e = plots.parser.from_latex(r"\sqrt{\frac{x}{2}}")
    assert e[0].parent is e
    assert e[0].radicand.parent is e[0]
    r = e[0].radicand
    assert r[0].parent is r
    n, d = r[0].numerator, r[0].denominator
    assert n.parent is d.parent is r[0]
    assert n[0].parent is n
    assert d[0].parent is d
