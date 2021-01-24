from . import abstractwrapped

class Ceil(abstractwrapped.AbstractWrapped):
    def __init__(self, argument, parent=None):
        super().__init__(argument, "⌈", "⌉", parent=parent)
