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

from jinja2 import Environment, PackageLoader

jinja_env = Environment(loader=PackageLoader('plots', 'shaders'))

GREEK_LETTERS = {
    'Alpha': 'Α',
    'Beta': 'Β',
    'Chi': 'Χ',
    'Delta': 'Δ',
    'Epsilon': 'Ε',
    'Eta': 'Η',
    'Gamma': 'Γ',
    'Iota': 'Ι',
    'Kappa': 'Κ',
    'Lambda': 'Λ',
    'Mu': 'Μ',
    'Nu': 'Ν',
    'Omega': 'Ω',
    'Omicron': 'Ο',
    'Phi': 'Φ',
    'Pi': 'Π',
    'Psi': 'Ψ',
    'Rho': 'Ρ',
    'Sigma': 'Σ',
    'Tau': 'Τ',
    'Theta': 'Θ',
    'Upsilon': 'Υ',
    'Xi': 'Ξ',
    'Zeta': 'Ζ',
    'alpha': 'α',
    'beta': 'β',
    'chi': 'χ',
    'delta': 'δ',
    'epsilon': 'ε',
    'eta': 'η',
    'gamma': 'γ',
    'iota': 'ι',
    'kappa': 'κ',
    'lambda': 'λ',
    'mu': 'μ',
    'nu': 'ν',
    'omega': 'ω',
    'omicron': 'ο',
    'phi': 'φ',
    "varphi": "φ",
    'pi': 'π',
    'psi': 'ψ',
    'rho': 'ρ',
    'sigma': 'σ',
    'tau': 'τ',
    'theta': 'θ',
    'upsilon': 'υ',
    'xi': 'ξ',
    'zeta': 'ζ'
}

GREEK_LETTERS_INVERSE = {char: name for name, char in GREEK_LETTERS.items()}
GREEK_REGEXES = GREEK_LETTERS.copy()
# stops a ψ being inserted while typing epsilon or upsilon
GREEK_REGEXES['(?<![EUeu])psi'] = GREEK_REGEXES.pop('psi')
# substrings must go second for regex to work
FUNCTIONS = "asech acsch acosech acoth sech csch cosech coth asec acsc acosec acot arcsec arccsc arccosec arccot sec csc cosec cot asinh acosh atanh sinh cosh tanh asin acos atan arcsin arccos arctan sinc sin cos tan exp log ln lg sign sgn".split()
BINARY_OPERATORS = ("+", "-", "*", "=")

SUP_ATOMS = "⁰¹²³⁴⁵⁶⁷⁸⁹ⁱⁿ"
SUP_CHARS = SUP_ATOMS + "⁺⁻⁽⁾"
SUP_TRAFO = str.maketrans(SUP_CHARS, "0123456789in+-()")
SUB_ATOMS = "₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₕₖₗₘₙₚₛₜ"
SUB_CHARS = SUB_ATOMS + "₊₋₍₎"
SUB_TRAFO = str.maketrans(SUB_CHARS, "0123456789aeoxhklmnpst+-()")

