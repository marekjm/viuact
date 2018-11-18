import collections
import hashlib

import exceptions
import group_types
import token_types


DEFAULT_REGISTER_SET = 'local'
LOCAL_REGISTER_SET = 'local'
# FIXME Should be 'closure_local' but current master code does not
# recognise this as a register set name and uses just the index to bind
# closure-local registers.
# CLOSURE_LOCAL_REGISTER_SET = 'closure_local'
CLOSURE_LOCAL_REGISTER_SET = ''
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
    def __init__(self, upper = None):
        self.next_slot = {
            'local': 1,
            'static': 0,
            'parameters': 0,
        }
        self.name_to_slot = {}
        self.last_used_slot = None
        self.nested_fns = []
        self.upper = upper
        self.used_upper_slots = {}

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
        if name not in self.name_to_slot and self.upper is not None:
            slot = self.upper.slot_of(name)
            self.used_upper_slots[name] = {
                'upper': slot,
                'local': self.get_slot(name),
            }
            return self.last_used_slot
        self.last_used_slot = self.name_to_slot[name]
        return self.last_used_slot

    def has_slot(self, name):
        return (name in self.name_to_slot)


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

        if source is None:
            raise exceptions.Source_cannot_be_void('source cannot be void', of_type)

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


def check_function_visibility(expr, meta):
    if meta is None:
        return

    return

    name = expr.to()
    if (name not in meta['functions']) and (name not in meta['local_functions']):
        raise Exception('call to undefined function', name)


def emit_expr(body : list, expr, state : State, slot : Slot = None, must_emit : bool = False, meta = None):
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
            body = body,
            call_expr = expr,
            state = state,
            slot = slot,
            meta = meta,
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
    elif leader_type is group_types.Function:
        nested_body = []
        nested_state = State(state)
        emit_function(
            nested_body,
            expr,
            nested_state,
            None,
        )
        for fn in nested_state.nested_fns:
            state.nested_fns.append(fn)

        if nested_state.used_upper_slots:
            nested_body[0].text = nested_body[0].text.replace('.function:', '.closure:')
            bd = []
            for each in nested_body:
                if type(each) is Verbatim and each.text.startswith('allocate_registers '):
                    continue
                bd.append(each)
            nested_body = bd

        if nested_state.used_upper_slots:
            if slot is None:
                slot = state.get_slot(str(expr.name.token))
            body.append(Verbatim('closure {} {}'.format(
                slot.to_string(),
                '{}/{}'.format(
                    str(expr.name.token),
                    len(expr.arguments),
                )
            )))
            for _, nested_slot in nested_state.used_upper_slots.items():
                body.append(Verbatim('capturecopy {} {} {}'.format(
                    slot.to_string(),
                    Slot(None, nested_slot['local'].index, CLOSURE_LOCAL_REGISTER_SET).to_string(),
                    nested_slot['upper'].to_string(),
                )))

        state.nested_fns.append(nested_body)

        return None
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
        raise exceptions.Emitter_exception('expression could not be emitted', expr)


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

def emit_call(body : list, call_expr, state : State, slot : Slot, meta):
    name = call_expr.name
    args = call_expr.args

    if call_expr.to() in BUILTIN_FUNCTIONS:
        return emit_builtin_call(body, call_expr, state, slot)

    # print('function-call', call_expr, call_expr.to(), meta)
    check_function_visibility(call_expr, meta)

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

    to = '{}/{}'.format(call_expr.to(), len(args))
    if state.has_slot(call_expr.to()):
        to = state.slot_of(call_expr.to()).to_string()

    body.append(Call(
        to = to,
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

    if slot is None:
        slot = state.get_slot(None)

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


def emit_function(body : list, expr, state : State, slot : Slot):
    body.append(Verbatim('.function: {}/{}'.format(
        str(expr.name.token),
        len(expr.arguments),
    )))

    inner_body = []

    for i, each in enumerate(expr.arguments):
        source = Slot(
            None,
            i,
            PARAMETERS_REGISTER_SET,
        )
        dest = state.get_slot(
            str(each.token),
        )
        inner_body.append(Move.make_move(
            source,
            dest,
        ))
    if expr.arguments:
        inner_body.append(Verbatim(''))

    for each in expr.body:
        # Expressions evaluated at function-level are given anonymous
        # slots.
        # Why? Because they are not assigned to anything. If an
        # expression is assigned to an anonymous slot it can decide for
        # itself what to do with this situation; function calls will
        # return to void, literals and let-bindings will be created.
        emit_expr(
            body = inner_body,
            expr = each,
            state = state,
            meta = None,
        )
        inner_body.append(Verbatim(''))

    body.append(Verbatim('allocate_registers %{} local'.format(
        state.next_slot[LOCAL_REGISTER_SET],
    )))
    body.append(Verbatim(''))
    body.extend(inner_body)
    body.append(Move.make_move(
        state.last_used_slot,
        Slot(None, 0,)
    ))
    body.append(Verbatim('return'))
    body.append(Verbatim('.end'))

    return
