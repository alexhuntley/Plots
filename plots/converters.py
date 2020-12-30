from plots import formula
import sympy
from itertools import zip_longest

def elementlist_to_sympy(expr):
    if not expr:
        return None
    output = []
    operators = []
    prev = None
    for t in tokens(expr):
        # implicit multiplication
        if prev is not None \
           and not isinstance(prev, (formula.BinaryOperatorAtom, formula.OperatorAtom)) \
           and not isinstance(t, formula.BinaryOperatorAtom) \
           and not is_paren(prev, left=True) \
           and not is_paren(t, left=False):
            mult = formula.BinaryOperatorAtom("×")
            pop_operators(operators, output, precedence(mult))
            operators.append(mult)
        if isinstance(t, sympy.Basic):
            output.append(t)
        elif isinstance(t, formula.OperatorAtom):
            operators.append(t)
        elif isinstance(t, formula.BinaryOperatorAtom):
            if prev is None or is_paren(prev, left=True) or \
               isinstance(prev, (formula.BinaryOperatorAtom, formula.OperatorAtom)):
                # t is a unary prefix operator
                # it should only pop other prefix operators
                pop_operators(operators, output, precedence(t), only_unary=True)
                operators.append(formula.BinaryOperatorAtom("unary_minus"))
            else:
                # t is a binary or postfix unary operator
                pop_operators(operators, output, precedence(t))
                operators.append(t)
        elif is_paren(t, left=True):
            operators.append(t)
        elif is_paren(t, left=False):
            pop_operators(operators, output, 1000)
            if operators and is_paren(operators[-1], left=True):
                operators.pop()
        else:
            output.append(element_to_sympy(t))
        prev = t
    while operators:
        pop_operator(operators, output)
    if len(output) != 1:
        raise SyntaxError("Malformed expression")
    return output[0]

def tokens(elementlist):
    number = []
    for elem, next in zip_longest(elementlist.elements, elementlist.elements[1:]):
        if part_of_number(elem):
            number.append(elem.name)
            if not part_of_number(next):
                yield sympy.Number("".join(number))
                number = []
        elif isinstance(elem, formula.Atom):
            yield atom_to_symbol(elem, next)
        elif isinstance(elem, formula.SuperscriptSubscript) and elem.exponent:
            yield formula.BinaryOperatorAtom("^")
            yield elementlist_to_sympy(elem.exponent)
        else:
            yield elem

def element_to_sympy(elem):
    if isinstance(elem, formula.Frac):
        return sympy.Mul(elementlist_to_sympy(elem.numerator),
                         sympy.Pow(elementlist_to_sympy(elem.denominator), -1))
    elif isinstance(elem, formula.Abs):
        return sympy.Abs(elementlist_to_sympy(elem.argument))
    elif isinstance(elem, formula.Radical):
        index = elementlist_to_sympy(elem.index) or 2
        return sympy.Pow(elementlist_to_sympy(elem.radicand),
                         sympy.Pow(index, -1))
    else:
        raise NotImplementedError

def part_of_number(element):
    return isinstance(element, formula.Atom) \
        and (element.name.isdigit() or element.name == ".")

CONSTANTS = {
    "𝜋": sympy.pi,
    "𝑒": sympy.E,
    "𝑖": sympy.I,
}
def atom_to_symbol(elem, next):
    if isinstance(next, formula.SuperscriptSubscript) and next.subscript:
        subscript = elementlist_to_string(next.subscript)
        name = "{}_{}".format(elem.name, subscript)
    else:
        name = elem.name
    if name in CONSTANTS:
        return CONSTANTS[name]
    else:
        return sympy.Symbol(name)

def elementlist_to_string(elementlist):
    res = []
    for x in elementlist.elements:
        if not isinstance(x, formula.Atom):
            raise SyntaxError
        res.append(x.name)
    return "".join(res)

def is_paren(element, left=None):
    if not isinstance(element, formula.Paren):
        return False
    if left is None:
        return True
    return left == element.left

PRECEDENCES = {
    "−": 1,
    "+": 1,
    "×": 3,
    "unary_minus": 4,
    "^": 5,
}
def precedence(operator):
    if isinstance(operator, formula.OperatorAtom):
        return 2
    assert isinstance(operator, formula.BinaryOperatorAtom)
    return PRECEDENCES[operator.name]

OPERATORS = {
    "−": lambda x, y: sympy.Add(x, sympy.Mul(y, -1)),
    "+": sympy.Add,
    "×": sympy.Mul,
    "^": sympy.Pow,
    "sin": sympy.sin,
    "cos": sympy.cos,
    "exp": sympy.exp,
    "unary_minus": lambda x: sympy.Mul(x, -1),
}
def pop_operator(operators, output):
    op = operators.pop()
    if isinstance(op, formula.BinaryOperatorAtom) and op.name != "unary_minus":
        args = output[-2:]
        output[-2:] = []
        output.append(OPERATORS[op.name](*args))
    elif isinstance(op, formula.Paren):
        pass
    else:
        arg = output.pop()
        output.append(OPERATORS[op.name](arg))

def pop_operators(operators, output, current_precedence, only_unary=False):
    try:
        while operators and isinstance(operators[-1], (formula.BinaryOperatorAtom, formula.OperatorAtom)) \
              and not is_paren(operators[-1], left=True) and \
              current_precedence <= precedence(operators[-1]) and \
              (not only_unary or operators[-1].name == "unary_minus"):
            pop_operator(operators, output)
    except IndexError:
        raise SyntaxError("Unmatched parentheses")


def sympy_to_elementlist(expr):
    numer, denom = expr.as_numer_denom()
    if denom != 1:
        return formula.ElementList([formula.Frac(sympy_to_elementlist(numer).elements,
                                                 sympy_to_elementlist(denom).elements)])
    elif isinstance(expr, sympy.Symbol):
        return formula.ElementList([formula.Atom(expr.name)])
    elif expr is sympy.pi:
        return formula.ElementList([formula.Atom('π')])
    elif expr is sympy.E:
        return formula.ElementList([formula.Atom('e')])
    elif expr is sympy.I:
        return formula.ElementList([formula.Atom('i')])
    elif isinstance(expr, sympy.Number):
        return formula.ElementList([formula.BinaryOperatorAtom(ch) if ch == '-' else formula.Atom(ch) for ch in str(expr)])
    elif isinstance(expr, sympy.sin):
        return formula.ElementList([formula.OperatorAtom('sin'), formula.Paren('('),
                                    *sympy_to_elementlist(expr.args[0]).elements, formula.Paren(')')])
    elif expr is sympy.cos:
        return formula.ElementList([formula.OperatorAtom('cos')])
    elif isinstance(expr, sympy.Add):
        res = []
        for arg in expr.args:
            res.extend(sympy_to_elementlist(arg).elements)
            res.append(formula.BinaryOperatorAtom('+'))
        del res[-1]
        return formula.ElementList(res)
    elif isinstance(expr, sympy.Mul):
        res = []
        for arg in expr.args:
            if isinstance(arg, sympy.Add):
                res.append(formula.Paren('('))
            res.extend(sympy_to_elementlist(arg).elements)
            if isinstance(arg, sympy.Add):
                res.append(formula.Paren(')'))
        return formula.ElementList(res)
    elif isinstance(expr, sympy.Pow):
        x = sympy_to_elementlist(expr.args[0])
        supersub = formula.SuperscriptSubscript()
        supersub.exponent = sympy_to_elementlist(expr.args[1])
        supersub.update_lists()
        return x + formula.ElementList([supersub])
    else:
        raise NotImplementedError(expr.func)
