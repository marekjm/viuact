import collections
import hashlib

import group_types
import token_types


DEFAULT_REGISTER_SET = 'local'
LOCAL_REGISTER_SET = 'local'
PARAMETERS_REGISTER_SET = 'parameters'

BUILTIN_FUNCTIONS = (
    'print',

    'actor',
    'Std::Actor::join',
    'Std::Actor::send',
    'Std::Actor::receive',

    'defer',
)

IGNORE_VALUE = '_'
INFINITE_DURATION = 'infinity'


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

    @staticmethod
    def to_address(slot):
        return ('void' if slot is None else slot.to_string())

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

class Move:
    MOVE = 'move'
    COPY = 'copy'

    @staticmethod
    def make_move(source, dest):
        return Move(
            Move.MOVE,
            source,
            dest,
        )

    @staticmethod
    def make_copy(source, dest):
        return Move(
            Move.COPY,
            source,
            dest,
        )

    def __init__(self, of_type : str, source : Slot, dest : Slot):
        self.of_type = of_type
        self.source = source
        self.dest = dest

    def to_string(self):
        return '{} {} {}'.format(
            self.of_type,
            self.dest.to_string(),
            self.source.to_string(),
        )

class Call:
    class Kind:
        Synchronous = 'call'
        Actor = 'process'
        Deferred = 'defer'

    def __init__(self, to : str, slot : Slot, kind = Kind.Synchronous):
        self.to = to
        self.slot = slot
        self.kind = kind

    def to_string(self):
        return '{kind} {dest} {fn}'.format(
            kind = self.kind,
            dest = Slot.to_address(self.slot),
            fn = self.to,
        )


def emit_expr(body : list, expr, state : State, slot : Slot = None, must_emit : bool = False):
    leader_type = type(expr)

    if leader_type is group_types.Let_binding:
        return emit_let(
            body,
            expr,
            state,
            slot,
        )
    elif leader_type is group_types.Function_call:
        return emit_call(
            body,
            expr,
            state,
            slot,
        )
    elif leader_type is group_types.Actor_call:
        return emit_actor_call(
            body,
            expr,
            state,
            slot,
        )
    elif leader_type is group_types.Operator_call:
        return emit_operator_call(
            body,
            expr,
            state,
            slot,
        )
    elif leader_type is group_types.If:
        return emit_if(
            body,
            expr,
            state,
            slot,
        )
    elif leader_type is group_types.Name_ref:
        evaluated_slot = state.slot_of(str(expr.name.token))
        if slot is not None and must_emit:
            body.append(Move.make_copy(
                dest = slot,
                source = evaluated_slot,
            ))
            return slot
        return evaluated_slot
    elif leader_type is token_types.String:
        if slot is None:
            slot = state.get_slot(None)
        body.append(Ctor(
            'text',
            slot,
            str(expr.token),
        ))
        return slot
    elif leader_type is token_types.Integer:
        if slot is None:
            slot = state.get_slot(None)
        body.append(Ctor(
            'integer',
            slot,
            str(expr.token),
        ))
        return slot
    elif leader_type is token_types.Timeout:
        if slot is not None:
            raise Exception('timeouts are not first class values')
        body.append(Timeout(
            str(expr.token),
        ))
        return slot
    else:
        raise Exception('expression could not be emitted', expr)


def emit_let(body : list, let_expr, state : State, slot : Slot):
    # Let-bindings always create their own slots.
    name = str(let_expr.name.token)
    if name == IGNORE_VALUE:
        slot = None
    else:
        slot = state.get_slot(name)
    emit_expr(body, let_expr.value, state, slot)
    return slot


def emit_builtin_call(body : list, call_expr, state : State, slot : Slot):
    args = call_expr.args

    if call_expr.to() == 'print':
        body.append(Verbatim('print {}'.format(
            emit_expr(body, args[0], state).to_string()
        )))
    elif call_expr.to() == 'Std::Actor::join':
        timeout = (args[1] if len(args) > 1 else token_types.Timeout(INFINITE_DURATION))
        body.append(Verbatim('join {} {} {}'.format(
            Slot.to_address(slot),
            emit_expr(body, args[0], state).to_string(),
            str(timeout.token),
        )))
    elif call_expr.to() == 'Std::Actor::receive':
        timeout = (args[0] if args else token_types.Timeout(INFINITE_DURATION))
        body.append(Verbatim('receive {} {}'.format(
            Slot.to_address(slot),
            str(timeout.token),
        )))
    elif call_expr.to() == 'Std::Actor::send':
        pid_slot = emit_expr(body, args[0], state)
        message_slot = emit_expr(body, args[1], state)
        body.append(Verbatim('send {} {}'.format(
            pid_slot.to_string(),
            message_slot.to_string(),
        )))
    else:
        raise Exception('unimplemented built-in', call_expr.to())

def emit_call(body : list, call_expr, state : State, slot : Slot):
    name = call_expr.name
    args = call_expr.args

    print(call_expr, call_expr.to())
    if call_expr.to() in BUILTIN_FUNCTIONS:
        return emit_builtin_call(body, call_expr, state, slot)

    applied_args = []
    for i, each in enumerate(args):
        arg_slot = state.get_slot(None)
        applied_args.append(emit_expr(body, each, state, arg_slot))

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i,
            each.index,
        )))

    if slot is not None:
        slot = state.slot_of(slot.name)
    body.append(Call(
        to = '{}/{}'.format(call_expr.to(), len(args)),
        slot = slot,
    ))

    return slot


def emit_actor_call(body : list, call_expr, state : State, slot : Slot):
    name = call_expr.name
    args = call_expr.args

    if call_expr.to() in BUILTIN_FUNCTIONS:
        raise Exception('cannot launch built-in function in an actor', call_expr)

    applied_args = []
    for i, each in enumerate(args):
        arg_slot = state.get_slot(None)
        applied_args.append(emit_expr(body, each, state, arg_slot))

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i,
            each.index,
        )))

    if slot is not None:
        slot = state.slot_of(slot.name)
    body.append(Call(
        to = '{}/{}'.format(call_expr.to(), len(args)),
        slot = slot,
        kind = Call.Kind.Actor,
    ))

    return slot


def emit_operator_call(body : list, call_expr, state : State, slot : Slot):
    name = call_expr.operator
    args = call_expr.args

    applied_args = []
    for i, each in enumerate(args):
        arg_slot = state.get_slot(None)
        applied_args.append(emit_expr(body, each, state, arg_slot))

    if slot is not None:
        slot = state.slot_of(slot.name)

    operator_names = {
        '+': 'add',
        '-': 'sub',
        '*': 'mul',
        '/': 'div',
        '=': 'eq',
    }

    body.append(Verbatim('{} {} {} {}'.format(
        operator_names[str(name.token)],
        slot.to_string(),
        applied_args[0].to_string(),
        applied_args[1].to_string(),
    )))

    return slot


def emit_if(body : list, if_expr, state : State, slot : Slot):
    condition = if_expr.condition
    arms = if_expr.arms

    cond_slot = state.get_slot(None)
    emit_expr(body, condition, state, cond_slot)

    true_arm_id = 'if_arm_{}'.format(hashlib.sha1(repr(arms[0]).encode('utf-8')).hexdigest())
    false_arm_id = 'if_arm_{}'.format(hashlib.sha1(repr(arms[1]).encode('utf-8')).hexdigest())
    if_end_id = 'if_end_{}'.format(hashlib.sha1(repr(if_expr).encode('utf-8')).hexdigest())

    body.append(Verbatim('if {} {} {}'.format(
        cond_slot.to_string(),
        true_arm_id,
        false_arm_id,
    )))

    if slot is None:
        slot = state.get_slot(None)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(true_arm_id)))
    emit_expr(body, arms[0], state, slot, must_emit = True)
    body.append(Verbatim('jump {}'.format(if_end_id)))

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(false_arm_id)))
    emit_expr(body, arms[1], state, slot, must_emit = True)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(if_end_id)))

    return slot
