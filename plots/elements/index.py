import re
from plots.data import GREEK_REGEXES, FUNCTIONS, BINARY_OPERATORS, GREEK_LETTERS

def string_to_names(string):
    regex = r"sum|prod|sqrt|nthroot|floor|ceil|."
    regex = "|".join(GREEK_REGEXES) + "|" + "|".join(FUNCTIONS) + "|" + regex
    names = re.findall(regex, string)
    return names

def name_to_element(name):
    if name == 'sqrt':
        return radical.Radical([])
    elif name == 'nthroot':
        return radical.Radical([], index=[])
    elif name == 'sum':
        return sum.Sum()
    elif name == 'prod':
        return sum.Sum(char="∏")
    elif name == 'floor':
        return floor.Floor([])
    elif name == 'ceil':
        return ceil.Ceil([])
    elif name in FUNCTIONS:
        return atom.OperatorAtom(name)
    elif name in BINARY_OPERATORS:
        return atom.BinaryOperatorAtom(name)
    elif len(name) == 1:
        return atom.Atom(name)
    elif name in GREEK_LETTERS:
        return atom.Atom(GREEK_LETTERS[name])
    else:
        return atom.OperatorAtom(name)

from . import sum
from . import paren
from . import radical
from . import frac
from . import supersubscript
from . import atom
from . import floor
from . import ceil
