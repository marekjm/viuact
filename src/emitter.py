import collections

import group_types
import token_types


class Slot(collections.namedtuple('Slot', ('name', 'index'))):
    pass

class State:
    def __init__(self):
        self.next_slot = 1
        self.name_to_slot = {}

    def get_slot(self, name):
        if name not in self.name_to_slot:
            self.name_to_slot[name] = self.next_slot
            self.next_slot += 1
        return Slot(name, self.name_to_slot[name])


class Verbatim:
    def __init__(self, text):
        self.text = text

class Ctor:
    def __init__(self, of_type : str, slot : Slot, value : str):
        self.of_type = of_type
        self.slot = slot
        self.value = value


def emit_let(body : list, let_expr, state : State):
    print('let', let_expr)
    name = let_expr.name
    value = let_expr.value

    expr_type = type(value)
    if expr_type is token_types.String:
        body.append(Ctor(
            'text',
            state.get_slot(str(name.token)),
            str(value.token),
        ))
