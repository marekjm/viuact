import collections

import group_types
import token_types


DEFAULT_REGISTER_SET = 'local'


class Slot:
    def __init__(self, name, index, register_set = DEFAULT_REGISTER_SET):
        self.name = name
        self.index = index
        self.register_set = register_set

    def __str__(self):
        return '{} = %{} {}'.format(
            self.name,
            self.index,
            self.register_set,
        )

    def is_void(self):
        return self.index is None

    def to_string(self):
        return '%{} {}'.format(
            self.index,
            self.register_set,
        )


class State:
    def __init__(self):
        self.next_slot = {
            'local': 1,
            'static': 0,
            'parameters': 0,
        }
        self.name_to_slot = {}
        self.last_used_slot = None

    def get_slot(self, name, register_set = DEFAULT_REGISTER_SET):
        if name not in self.name_to_slot:
            self.name_to_slot[name] = Slot(
                name,
                self.next_slot[register_set],
                register_set,
            )
            self.next_slot[register_set] += 1
        self.last_used_slot = self.name_to_slot[name]
        return self.last_used_slot

    def slot_of(self, name):
        self.last_used_slot = self.name_to_slot[name]
        return self.last_used_slot


class Verbatim:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return 'Verbatim: {}'.format(repr(self.text))

    def to_string(self):
        return self.text

class Ctor:
    def __init__(self, of_type : str, slot : Slot, value : str):
        self.of_type = of_type
        self.slot = slot
        self.value = value

    def to_string(self):
        return '{} {} {}'.format(
            self.of_type,
            self.slot.to_string(),
            self.value,
        )

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
    elif leader_type is group_types.Name_ref:
        return state.slot_of(str(expr.name.token))
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
        applied_args.append(emit_expr(body, each, state))
    print(applied_args)

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i,
            each.index,
        )))

    body.append(Verbatim('call %{} local {}/{}'.format(
        state.get_slot(None).index,
        str(name.token),
        len(args),
    )))
