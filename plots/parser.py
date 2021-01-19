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

from lark import Lark, Transformer

from plots import formula

class LatexTransformer(Transformer):
    def list(self, items):
        return formula.ElementList(elements=items)

    def atom(self, items):
        return formula.Atom(items[0])

    def times(self, _):
        return formula.BinaryOperatorAtom("×")

    def plus(self, _):
        return formula.BinaryOperatorAtom("+")

    def minus(self, _):
        return formula.BinaryOperatorAtom("−")

    def equals(self, _):
        return formula.BinaryOperatorAtom("=")

    def operator(self, items):
        return formula.OperatorAtom(items[0])

    def OPNAME(self, tok):
        return tok.value

    def superscript(self, items):
        return formula.SuperscriptSubscript(exponent=items[0])

    def subscript(self, items):
        return formula.SuperscriptSubscript(subscript=items[0])

    def superscriptsubscript(self, items):
        return formula.SuperscriptSubscript(subscript=items[0], exponent=items[1])

    def frac(self, items):
        return formula.Frac(numerator=items[0], denominator=items[1])

    def sqrt(self, items):
        return formula.Radical(items[0])

    def nthroot(self, items):
        return formula.Radical(items[1], index=items[0])

    def abs(self, items):
        return formula.Abs(items[0])

    def PAREN(self, tok):
        return tok.value.replace("\\", "")

    def paren(self, items):
        return formula.Paren(items[0])

    def sum(self, items):
        return formula.Sum(char="Σ", bottom=items[0], top=items[1])

    def prod(self, items):
        return formula.Sum(char="Π", bottom=items[0], top=items[1])

latex_parser = Lark(r"""
list : element*
?blist : "{" list "}"
?element : atom | binary | operator | supersub | frac | radical | abs | paren | sum | prod

atom : LETTER | DIGIT | "."

TIMES : "\\times"
binary : TIMES -> times
       | "+" -> plus
       | "-" -> minus
       | "=" -> equals

OPNAME : LETTER+
operator : "\\operatorname{" OPNAME "}"

supersub : "_" blist -> subscript
         | "^" blist -> superscript
         | "_" blist "^" blist -> superscriptsubscript

frac.10 : "\\frac" blist blist

radical : "\\sqrt" blist -> sqrt
        | "\\sqrt" "[" list "]" blist -> nthroot

abs : "\\abs" blist

PAREN : "(" | "[" | "\\{" | ")" | "]" | "\\}"
paren : PAREN

sum : "\\sum" "_" blist "^" blist
prod : "\\prod" "_" blist "^" blist

%import common.LETTER
%import common.DIGIT

%import common.WS
%ignore WS
""", start='list', parser="lalr", transformer=LatexTransformer())

def from_latex(string):
    return latex_parser.parse(string)
