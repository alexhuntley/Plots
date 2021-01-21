from plots.cursor import Cursor
import plots.formula as f
from plots.parser import from_latex
from plots.utils import Direction

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
