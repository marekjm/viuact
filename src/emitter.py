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
    'Std::Actor::receive',
    'Std::Actor::self',
    'Std::Actor::send',

    'Std::String::concat',
    'Std::String::to_string',

    'Std::Vector::at',
    'Std::Vector::push',
)

IGNORE_VALUE = '_'
INFINITE_DURATION = 'infinity'


class Slot:
    def __init__(self, name, index, register_set = DEFAULT_REGISTER_SET):
        self.name = name
        self.index = index
        self.register_set = register_set
        self.is_pointer = False

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

    def to_string(self, pointer_dereference = None):
        as_pointer = self.is_pointer
        if pointer_dereference is not None:
            as_pointer = pointer_dereference
        return '{}{} {}'.format(
            ('*' if as_pointer else '%'),
            self.index,
            self.register_set,
        )


class State:
    def __init__(self, upper, visible_fns, function_name):
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
        self.visible_fns = visible_fns
        if function_name is not None and type(function_name) is not str:
            raise TypeError(function_name)
        self.function_name = function_name

    def get_slot(self, name, register_set = DEFAULT_REGISTER_SET, anonymous = False):
        if name is None and not anonymous:
            raise Exception('requested slot without a name')

        if anonymous:
            slot = Slot(
                None,
                self.next_slot[register_set],
                register_set,
            )
            self.next_slot[register_set] += 1
            self.last_used_slot = slot
            return slot

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
        Tail = 'tailcall'
        Deferred = 'defer'

    def __init__(self, to : str, slot : Slot, kind = Kind.Synchronous):
        self.to = to
        self.slot = slot
        self.kind = kind

    def to_string(self):
        return '{kind} {dest} {fn}'.format(
            kind = self.kind,
            dest = (
                ''
                if self.kind in (Call.Kind.Tail, Call.Kind.Deferred,)
                else Slot.to_address(self.slot)
            ),
            fn = self.to,
        )


def emit_expr(
        body : list,    # Body is a list of instructions which were emitted by
                        # already processed expressions. New instructions that
                        # will be emitted by this expression should be appended
                        # to it.
        expr,   # Current expression to emit. A single expression may evaluate
                # to a single expression (if it is a simple literal ctor), or to
                # a complex sequence of instructions (as is the case with
                # function calls, compound expressions, etc.).
        state : State,  # Current state of the function's register sets. It is
                        # used to request new slots and fetch indexes of
                        # existing variables.
        slot : Slot = None, # Target slot into which the current expression
                            # should return its final value. This is assigned by
                            # the parent expression. If the slot is none the
                            # value produced by the expression should be
                            # discarded.
        must_emit : bool = False,   # Specifies whether the expression must emit
                                    # at least one instruction. This is
                                    # sometimes required to produce valid
                                    # instruction sequences, and to represent
                                    # tempoarary values.
        meta = None,    # Various meta data about the function and its
                        # environment. It contains information about visible
                        # functions, imports, etc.
        toplevel = False,   # Whether this expression is a top-level expression
                            # inside a function's body. A top-level expression
                            # may avoid storing its result if it is not
                            # presistent (e.g. a let binding will emit, a
                            # temporary may not).
    ):
    leader_type = type(expr)

    if leader_type is group_types.Let_binding:
        slot = emit_let(
            body,
            expr,
            state,
            slot,
        )
        state.last_used_slot = slot
        return slot
    elif leader_type is group_types.Function_call:
        if (not toplevel) and (slot is None):
            slot = state.get_slot(None, anonymous = True)
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
    elif leader_type is group_types.Tail_call:
        return emit_tail_call(
            body,
            expr,
            state,
            slot,
        )
    elif leader_type is group_types.Deferred_call:
        return emit_deferred_call(
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
    elif leader_type is group_types.Field_assignment:
        return emit_field_assignment(
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
        if must_emit:
            if slot is None:
                slot = state.get_slot(None)
            body.append(Move.make_copy(
                dest = slot,
                source = evaluated_slot,
            ))
            return slot
        return evaluated_slot
    elif leader_type is group_types.Id:
        name = expr.name[0]

        if str(name.token).isupper():
            return emit_function_ref(
                body,
                expr,
                state,
                slot,
                must_emit,
                meta,
            )
        else:
            return emit_struct_field_access(
                body,
                expr,
                state,
                slot,
                must_emit,
                meta,
            )
    elif leader_type is group_types.Function:
        nested_body = []
        v = meta.nested_in(state.function_name)
        real_name = '{}::{}_{}'.format(
            state.function_name,
            str(expr.name.token),
            hashlib.sha1(repr(expr).encode('utf-8')).hexdigest(),
        )
        v.add_function(
            name = str(expr.name.token),
            arity = len(expr.arguments),
            real_name = real_name,
            from_module = meta.prefix,
        )
        meta.add_function(
            name = str(expr.name.token),
            arity = len(expr.arguments),
            real_name = real_name,
            from_module = meta.prefix,
        )
        nested_state = State(
            upper = state,
            visible_fns = v,
            function_name = state.function_name,
        )
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
                    state.visible_fns.real_name(str(expr.name.token), token = expr.name.token),
                    len(expr.arguments),
                )
            )))
            for _, nested_slot in nested_state.used_upper_slots.items():
                body.append(Verbatim('capturecopy {} {} {}'.format(
                    slot.to_string(),
                    Slot(None, nested_slot['local'].index, CLOSURE_LOCAL_REGISTER_SET).to_string(),
                    nested_slot['upper'].to_string(),
                )))

        state.nested_fns.append((real_name, nested_body,))

        return None
    elif leader_type is token_types.String:
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Ctor(
            'text',
            slot,
            str(expr.token),
        ))
        return slot
    elif leader_type is token_types.Integer:
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
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
    elif leader_type is token_types.Boolean:
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        # Booleans are constructed by creating an integer that would be interpreted as
        # false and using the "not constructor" idiom (since Viua has a representation of
        # boolean values, but lacks a direct constructor for them).
        body.append(Verbatim('izero {dest}'.format(dest = slot.to_string())))

        # After the integer is stored, we convert it to a boolean by negating it. This
        # step also inverts the logical value that is contained in a register, effectively
        # turning it into a "true".
        body.append(Verbatim('not {dest} {dest}'.format(dest = slot.to_string())))

        if str(expr.token) == 'false':
            # If we need a "false" value a second negation is needed.
            body.append(Verbatim('not {dest} {dest}'.format(dest = slot.to_string())))
        return slot
    elif leader_type is group_types.Struct:
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Ctor(
            'struct',
            slot,
            '',
        ))
        return slot
    elif leader_type is group_types.Vector:
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Ctor(
            'vector',
            slot,
            '',
        ))
        return slot
    elif leader_type is group_types.Compound_expression:
        return emit_compound_expr(
            body,
            expr,
            state,
            slot,
            must_emit,
            meta,
        )
    elif leader_type is list:
        raise exceptions.Emitter_exception(
            'expression could not be emitted, try removing parentheses surrounding it', expr)
    else:
        raise exceptions.Emitter_exception('expression could not be emitted', expr)


def emit_let(body : list, let_expr, state : State, slot : Slot):
    # Let-bindings always create their own slots.
    name = str(let_expr.name.token)
    if name == IGNORE_VALUE:
        slot = None
    else:
        slot = state.get_slot(name)
    emit_expr(
        body = body,
        expr = let_expr.value,
        state = state,
        slot = slot,
        must_emit = False,
        meta = None,
        toplevel = False,
    )
    return slot


def emit_builtin_call(body : list, call_expr, state : State, slot : Slot):
    args = call_expr.args

    if call_expr.to() == 'print':
        slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('print {}'.format(
            slot.to_string()
        )))
    elif call_expr.to() == 'Std::Actor::join':
        timeout = (args[1] if len(args) > 1 else token_types.Timeout(INFINITE_DURATION))
        body.append(Verbatim('join {} {} {}'.format(
            Slot.to_address(slot),
            emit_expr(
                body = body,
                expr = args[0],
                state = state,
                slot = None,
                must_emit = False,
                meta = None,
                toplevel = False,
            ).to_string(),
            str(timeout.token),
        )))
    elif call_expr.to() == 'Std::Actor::receive':
        timeout = (args[0] if args else token_types.Timeout(INFINITE_DURATION))
        body.append(Verbatim('receive {} {}'.format(
            Slot.to_address(slot),
            str(timeout.token),
        )))
    elif call_expr.to() == 'Std::Actor::send':
        pid_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        message_slot = emit_expr(
            body = body,
            expr = args[1],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('send {} {}'.format(
            pid_slot.to_string(),
            message_slot.to_string(),
        )))
    elif call_expr.to() == 'Std::Actor::self':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Verbatim('self {}'.format(
            slot.to_string(),
        )))
        return slot
    elif call_expr.to() == 'Std::String::to_string':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Verbatim('text {} {}'.format(
            slot.to_string(),
            emit_expr(
                body = body,
                expr = args[0],
                state = state,
                slot = None,
                must_emit = False,
                meta = None,
                toplevel = False,
            ).to_string(),
        )))
        return slot
    elif call_expr.to() == 'Std::String::concat':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Verbatim('textconcat {} {} {}'.format(
            slot.to_string(),
            emit_expr(
                body = body,
                expr = args[0],
                state = state,
                slot = None,
                must_emit = False,
                meta = None,
                toplevel = False,
            ).to_string(),
            emit_expr(
                body = body,
                expr = args[1],
                state = state,
                slot = None,
                must_emit = False,
                meta = None,
                toplevel = False,
            ).to_string(),
        )))
        return slot
    elif call_expr.to() == 'Std::Vector::push':
        vector_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        value_slot = emit_expr(
            body = body,
            expr = args[1],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('vpush {} {}'.format(
            vector_slot.to_string(),
            value_slot.to_string(),
        )))

        # We don't create or use a slot provided by the caller because we need
        # to return the slot in which the vector resides.
        return vector_slot
    elif call_expr.to() == 'Std::Vector::at':
        vector_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        index_slot = emit_expr(
            body = body,
            expr = args[1],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Verbatim('vat {} {} {}'.format(
            slot.to_string(),
            vector_slot.to_string(),
            index_slot.to_string(),
        )))

        slot.is_pointer = True
        return slot
    else:
        raise Exception('unimplemented built-in', call_expr.to())

    return slot

def emit_call(body : list, call_expr, state : State, slot : Slot, meta):
    name = call_expr.name
    args = call_expr.args

    name_token = None
    if type(name) is group_types.Id:
        name_token = name.name[-1].token
    else:
        name_token = name.token

    if call_expr.to() in BUILTIN_FUNCTIONS:
        return emit_builtin_call(body, call_expr, state, slot)

    fn_name = call_expr.to()

    if not state.has_slot(fn_name):
        fn_name = state.visible_fns.real_name(fn_name, token = name_token)

    applied_args = []
    for i, each in enumerate(args):
        applied_args.append(emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        ))

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        # FIXME if name is None (anonuymous slot) make move not copy
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i,
            each.index,
        )))

    to = '{}/{}'.format(fn_name, len(args))
    if state.has_slot(fn_name):
        to = state.slot_of(fn_name).to_string()

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
        arg_slot = state.get_slot(None, anonymous = True)
        applied_args.append(emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = arg_slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        ))

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i,
            each.index,
        )))

    body.append(Call(
        to = '{}/{}'.format(call_expr.to(), len(args)),
        slot = slot,
        kind = Call.Kind.Actor,
    ))

    return slot


def emit_tail_call(body : list, call_expr, state : State, slot : Slot):
    name = call_expr.name
    args = call_expr.args

    if call_expr.to() in BUILTIN_FUNCTIONS:
        raise Exception('cannot tail call built-in function', call_expr)

    applied_args = []
    for i, each in enumerate(args):
        arg_slot = state.get_slot(None, anonymous = True)
        applied_args.append(emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = arg_slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        ))

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i,
            each.index,
        )))

    body.append(Call(
        to = '{}/{}'.format(call_expr.to(), len(args)),
        slot = None,
        kind = Call.Kind.Tail,
    ))

    return slot


def emit_deferred_call(body : list, call_expr, state : State, slot : Slot):
    name = call_expr.name
    args = call_expr.args

    applied_args = []
    for i, each in enumerate(args):
        arg_slot = state.get_slot(None, anonymous = True)
        applied_args.append(emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = arg_slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        ))

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i,
            each.index,
        )))

    body.append(Call(
        to = '{}/{}'.format(call_expr.to(), len(args)),
        slot = None,
        kind = Call.Kind.Deferred,
    ))

    return slot


def emit_operator_call(body : list, call_expr, state : State, slot : Slot):
    name = call_expr.operator
    args = call_expr.args

    applied_args = []
    for i, each in enumerate(args):
        applied_args.append(emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        ))

    if slot is None:
        slot = state.get_slot(None, anonymous = True)

    operator_names = {
        '+': 'add',
        '-': 'sub',
        '*': 'mul',
        '/': 'div',
        '=': 'eq',
        '<': 'lt',
        '<=': 'lte',
        '>': 'gt',
        '>=': 'gte',
        'not': 'not',
        'and': 'and',
        'or': 'or',
    }

    if str(name.token) == 'not':
        body.append(Verbatim('{} {} {}'.format(
            operator_names[str(name.token)],
            slot.to_string(),
            applied_args[0].to_string(),
        )))
    else:
        body.append(Verbatim('{} {} {} {}'.format(
            operator_names[str(name.token)],
            slot.to_string(pointer_dereference = False),
            applied_args[0].to_string(),
            applied_args[1].to_string(),
        )))
        slot.is_pointer = False

    return slot


def emit_if(body : list, if_expr, state : State, slot : Slot):
    condition = if_expr.condition
    arms = if_expr.arms

    cond_slot = emit_expr(
        body = body,
        expr = condition,
        state = state,
        slot = None,
        must_emit = True,
        meta = None,
        toplevel = False,
    )

    true_arm_id = 'if_arm_true_{}'.format(hashlib.sha1(
        repr(arms[0]).encode('utf-8') + repr(if_expr).encode('utf-8') + repr(id(arms[0])).encode('utf-8')
    ).hexdigest())
    false_arm_id = 'if_arm_false_{}'.format(hashlib.sha1(
        repr(arms[1]).encode('utf-8') + repr(if_expr).encode('utf-8') + repr(id(arms[1])).encode('utf-8')
    ).hexdigest())
    if_end_id = 'if_end_{}'.format(hashlib.sha1(repr(if_expr).encode('utf-8')).hexdigest())

    body.append(Verbatim('if {} {} {}'.format(
        cond_slot.to_string(),
        true_arm_id,
        false_arm_id,
    )))

    if slot is None:
        slot = state.get_slot(None, anonymous = True)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(true_arm_id)))
    emit_expr(
        body = body,
        expr = arms[0],
        state = state,
        slot = slot,
        must_emit = True,
        meta = None,
        toplevel = False,
    )
    body.append(Verbatim('jump {}'.format(if_end_id)))

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(false_arm_id)))
    emit_expr(
        body = body,
        expr = arms[1],
        state = state,
        slot = slot,
        must_emit = True,
        meta = None,
        toplevel = False,
    )

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(if_end_id)))

    state.last_used_slot = slot

    return slot


def emit_function(body : list, expr, state : State, slot : Slot):
    body.append(Verbatim('.function: {}/{}'.format(
        state.visible_fns.real_name(str(expr.name.token), token = expr.name.token),
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

    emit_expr(
        body = inner_body,
        expr = expr.body,
        state = state,
        slot = None,
        must_emit = False,
        meta = state.visible_fns,
        toplevel = False,
    )

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


def emit_compound_expr(body : list, expr, state : State, slot : Slot = None, must_emit : bool = False, meta = None):
    for each in expr.expressions[:-1]:
        emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = None,
            must_emit = False,
            meta = meta,
            toplevel = True,    # True because non-final expressions inside a
                                # compound expression do not need to return a
                                # visible value.
        )
    return emit_expr(
        body = body,
        expr = expr.expressions[-1],
        state = state,
        slot = slot,
        must_emit = must_emit,
        meta = meta,
        toplevel = False,
    )


def emit_field_assignment(body : list, expr, state : State, slot : Slot):
    slot = emit_expr(
        body = body,
        expr = expr.value,
        state = state,
        slot = slot,
    )

    field = expr.field
    base_target_slot = state.slot_of(str(field[0].token))

    field_name_slot = state.get_slot(None, anonymous = True)
    field_names = list(filter(lambda each: str(each.token) != '.', field[1:]))

    inner_struct_slot = None
    if len(field_names) > 1:
        inner_struct_slot = state.get_slot(None, anonymous = True)

    for i, field_name in enumerate(field_names[:-1]):
        body.append(Verbatim('atom {} {}'.format(
            field_name_slot.to_string(),
            repr(field_name.token),
        )))
        body.append(Verbatim('structat {} {} {}'.format(
            inner_struct_slot.to_string(),
            base_target_slot.to_string(i > 0),
            field_name_slot.to_string(),
        )))
        base_target_slot = inner_struct_slot

    field_name = str(field_names[-1].token)
    body.append(Verbatim('atom {} {}'.format(
        field_name_slot.to_string(),
        repr(field_name),
    )))

    target_is_pointer = None
    if inner_struct_slot is not None:
        target_is_pointer = True
    body.append(Verbatim('structinsert {} {} {}'.format(
        base_target_slot.to_string(target_is_pointer),
        field_name_slot.to_string(),
        slot.to_string(),
    )))

    # FIXME Figure out what to do if we want struct field updates to return values.
    # body.append(Verbatim('structat {} {} {}'.format(
    #     slot.to_string(),
    #     base_target_slot.to_string(inner_struct_slot is not None),
    #     field_name_slot.to_string(),
    # )))

    return slot


def emit_struct_field_access(body : list, expr, state : State, slot : Slot, must_emit = False, meta = None):
    field = expr.name
    base_source_slot = state.slot_of(str(field[0].token))

    field_name_slot = state.get_slot(None, anonymous = True)
    field_names = list(filter(lambda each: str(each.token) != '.', field[1:]))

    if slot is None:
        slot = state.get_slot(None, anonymous = True)

    for i, field_name in enumerate(field_names):
        body.append(Verbatim('atom {} {}'.format(
            field_name_slot.to_string(),
            repr(field_name.token),
        )))
        body.append(Verbatim('structat {} {} {}'.format(
            slot.to_string(),
            base_source_slot.to_string(i > 0),
            field_name_slot.to_string(),
        )))
        base_source_slot = slot

    slot.is_pointer = True
    return slot
