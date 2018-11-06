import collections

import group_types
import token_types


class Slot(collections.namedtuple('Slot', ('name', 'index'))):
    def is_void(self):
        return self[1] is None


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

    def __repr__(self):
        return 'Verbatim: {}'.format(repr(self.text))

class Ctor:
    def __init__(self, of_type : str, slot : Slot, value : str):
        self.of_type = of_type
        self.slot = slot
        self.value = value

class Call:
    def __init__(self, to : str, slot : Slot):
        self.to = name
        self.slot = slot


def emit_expr(body : list, expr, state : State):
    leader_type = type(expr)

    if leader_type is group_types.Let_binding:
        return emit_let(
            body,
            expr,
            state,
        )
    elif leader_type is group_types.Function_call:
        return emit_call(
            body,
            expr,
            state,
        )
    else:
        raise Exception('expression could not be emitted', expr)


def emit_let(body : list, let_expr, state : State):
    print('let', let_expr)
    name = let_expr.name
    value = let_expr.value

    expr_type = type(value)
    if expr_type is token_types.String:
        slot = state.get_slot(str(name.token))
        body.append(Ctor(
            'text',
            slot,
            str(value.token),
        ))
        return slot


def emit_call(body : list, call_expr, state : State):
    print('call', call_expr)
    name = call_expr.name
    args = call_expr.args

    print('    args:', args)
    applied_args = []
    for i, each in enumerate(args):
        print('    arg[{}]'.format(i), each)
        applied_args.append(emit_expr(each, body, state))
    print(applied_args)

    body.append(Verbatim('frame %{}'.format(len(args))))
