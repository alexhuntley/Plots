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

from lark import Lark, Transformer

from plots import elements

class LatexTransformer(Transformer):
    def list(self, items):
        return elements.ElementList(elements=items)

    def atom(self, items):
        return elements.Atom(items[0])

    def times(self, _):
        return elements.BinaryOperatorAtom("×")

    def plus(self, _):
        return elements.BinaryOperatorAtom("+")

    def minus(self, _):
        return elements.BinaryOperatorAtom("−")

    def equals(self, _):
        return elements.BinaryOperatorAtom("=")

    def operator(self, items):
        return elements.OperatorAtom(items[0].value)

    def superscript(self, items):
        return elements.SuperscriptSubscript(exponent=items[0])

    def subscript(self, items):
        return elements.SuperscriptSubscript(subscript=items[0])

    def subscriptsuperscript(self, items):
        return elements.SuperscriptSubscript(subscript=items[0], exponent=items[1])

    def frac(self, items):
        return elements.Frac(numerator=items[0], denominator=items[1])

    def sqrt(self, items):
        return elements.Radical(items[0])

    def nthroot(self, items):
        return elements.Radical(items[1], index=items[0])

    def abs(self, items):
        return elements.Abs(items[0])

    def floor(self, items):
        return elements.Floor(items[0])

    def ceil(self, items):
        return elements.Ceil(items[0])

    def paren(self, items):
        return elements.Paren(items[0].value.replace("\\", ""))

    def sum(self, items):
        return elements.Sum(char="∑", bottom=items[0], top=items[1])

    def prod(self, items):
        return elements.Sum(char="∏", bottom=items[0], top=items[1])

latex_parser = Lark(r"""
list : element*
?blist : "{" list "}"
?element : atom
         | binary
         | operator
         | supersub
         | frac
         | radical
         | abs
         | floor
         | ceil
         | paren
         | sum
         | prod
         | subscriptsuperscript

GREEK : "α".."ω" | "Α".."Ω"
SYMBOL : "." | "!"
atom : LETTER | GREEK | DIGIT | SYMBOL

TIMES : "\\times"
binary : TIMES -> times
       | "+" -> plus
       | "-" -> minus
       | "=" -> equals

OPNAME : LETTER+
operator : "\\operatorname{" OPNAME "}"

subscriptsuperscript.2 : "_" blist "^" blist
supersub : "_" blist -> subscript
         | "^" blist -> superscript

frac.10 : "\\frac" blist blist

radical : "\\sqrt" blist -> sqrt
        | "\\sqrt" "[" list "]" blist -> nthroot

abs : "\\abs" blist
floor : "\\floor" blist
ceil : "\\ceil" blist

PAREN : "(" | "[" | "\\{" | ")" | "]" | "\\}"
paren : PAREN

sum : "\\sum" "_" blist "^" blist
prod : "\\prod" "_" blist "^" blist

%import common.LETTER
%import common.DIGIT

%import common.WS
%ignore WS
""", start='list') # lalr seems to have problems with ']'

transformer = LatexTransformer()
def from_latex(string):
    return transformer.transform(latex_parser.parse(string))
