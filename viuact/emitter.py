import collections
import hashlib

from viuact import exceptions, group_types, token_types


DEFAULT_REGISTER_SET = 'local'
LOCAL_REGISTER_SET = 'local'
# FIXME Should be 'closure_local' but current master code does not
# recognise this as a register set name and uses just the index to bind
# closure-local registers.
# CLOSURE_LOCAL_REGISTER_SET = 'closure_local'
CLOSURE_LOCAL_REGISTER_SET = ''
PARAMETERS_REGISTER_SET = 'parameters'
ARGUMENTS_REGISTER_SET = 'arguments'

BUILTIN_FUNCTIONS = (
    'print',
    'echo',

    'actor',
    'Std::Actor::join',
    'Std::Actor::receive',
    'Std::Actor::self',
    'Std::Actor::send',

    'Std::Pid::eq',

    'Std::copy',
    'Std::move',

    'Std::String::at',
    'Std::String::concat',
    'Std::String::eq',
    'Std::String::size',
    'Std::String::substr',
    'Std::String::to_string',

    'Std::Integer::of_bytes',

    'Std::Vector::at',
    'Std::Vector::push',
    'Std::Vector::size',

    'Std::Pointer::take',

    'Io::read',
    'Io::write',
    'Io::close',
    'Io::wait',
    'Io::cancel',
)

IGNORE_VALUE = '_'
INFINITE_DURATION = 'infinity'


class Slot:
    def __init__(self, name, index, register_set = DEFAULT_REGISTER_SET):
        self.name = name
        self.index = index
        self.register_set = register_set
        self.is_pointer = False
        self.is_pointer_explicit = False

    def __eq__(self, other):
        if type(other) is not Slot:
            return False
        return (
                (self.index == other.index)
            and (self.register_set == other.register_set)
        )

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

    def is_anonymous(self):
        return self.name is None

    def become_anonymous(self):
        self.name = None
        return self

    def to_string(self, pointer_dereference = None):
        as_pointer = (self.is_pointer and not self.is_pointer_explicit)
        if pointer_dereference is not None:
            as_pointer = pointer_dereference
        return '{}{} {}'.format(
            ('*' if as_pointer else '%'),
            self.index,
            self.register_set,
        )

    def as_pointer(self):
        s = Slot(self.name, self.index, self.register_set)
        s.is_pointer = True
        return s


class State:
    class Allocation_tracker:
        class Slot_not_tracked(Exception):
            pass

        def __init__(self):
            self.slots = []

        def save(self, slot):
            self.slots.append(slot)

        def release(self, slot, safe = False):
            if slot is None:
                return
            if (slot not in self.slots):
                if not safe:
                    raise State.Allocation_tracker.Slot_not_tracked(slot)
                else:
                    return
            self.slots.remove(slot)

    def __init__(self, upper, visible_fns, function_name):
        self.tracker = None
        self.register_pressure = {
            'local': 0,
            'static': 0,
        }
        self.next_slot = {
            'local': 1,
            'static': 0,
            'parameters': 0,
        }
        self.free_slots = {
            'local': [],
            'static': [],
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
        self.branches_encountered = 0

    def track_slot_allocations(self, tracker):
        self.tracker = tracker

    def release_tracked_allocations(self, tracker):
        for each in tracker.slots:
            self.deallocate_slot(slot = each)
        self.tracker = None

    def allocate_slot(self, register_set):
        self.register_pressure[register_set] += 1

        slot_index = None
        if self.free_slots[register_set]:
            slot_index = self.free_slots[register_set].pop(0)
        else:
            slot_index = self.next_slot[register_set]
            self.next_slot[register_set] += 1

        if self.tracker:
            self.tracker.save(Slot(
                name = None,
                index = slot_index,
                register_set = register_set,
            ))

        return slot_index

    def deallocate_slot(self, name = None, slot = None):
        if (name is None) and (slot is None):
            raise Exception('slot and name cannot both be none')
        if (name is not None) and (slot is not None):
            raise Exception('slot and name cannot both not be none')

        if name is not None:
            if type(name) is not str:
                raise Exception('name must be a string, but is {}'.format(
                    str(type(name))[8:-2]))
            slot = self.name_to_slot.get(name)
            if slot is None:
                raise Exception('unknown name: {}'.format(name))
        else:
            for k, v in self.name_to_slot.items():
                if slot == v:
                    name = k
                    break

        if name is not None:
            del self.name_to_slot[name]

        self.free_slots[slot.register_set].append(slot.index)
        self.free_slots[slot.register_set].sort()

        if self.tracker:
            self.tracker.release(slot)

    def deallocate_slot_if_anonymous(self, slot):
        if not slot.is_anonymous():
            return
        self.deallocate_slot(slot = slot)

    def get_slot(self, name, register_set = DEFAULT_REGISTER_SET, anonymous = False):
        if name is None and not anonymous:
            raise Exception('requested non-anonymous slot without a name')

        if anonymous:
            slot = Slot(
                None,
                self.allocate_slot(register_set),
                register_set,
            )
            self.last_used_slot = slot
            return slot

        if name not in self.name_to_slot:
            self.name_to_slot[name] = Slot(
                name,
                self.allocate_slot(register_set),
                register_set,
            )
        self.last_used_slot = self.name_to_slot[name]
        return self.last_used_slot

    def name_slot(self, slot, name):
        self.name_to_slot[name] = slot

    def unname_slot(self, name):
        del self.name_to_slot[name]

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

    class Name_kind:
        Let_binding = 'let_binding'
        Function = 'function'
    def what_is_it(self, name):
        if name in self.name_to_slot:
            return State.Name_kind.Let_binding
        elif (name in self.nested_fns) or (name in self.visible_fns.functions):
            return State.Name_kind.Function
        return None


class Verbatim:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return 'Verbatim: {}'.format(repr(self.text))

    def to_string(self):
        return self.text

class Ctor:
    TAG_ENUM_TAG_FIELD = repr('tag')
    TAG_ENUM_VALUE_FIELD = repr('value')

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
    DELETE = 'delete'

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

    @staticmethod
    def make_delete(source):
        return Move(
            Move.DELETE,
            source,
            None,
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
            (self.dest.to_string() if self.dest is not None else ''),
            self.source.to_string(),
        )

class Call:
    class Kind:
        Synchronous = 'call'
        Actor = 'process'
        Tail = 'tailcall'
        Deferred = 'defer'
        Watchdog = 'watchdog'

    def __init__(self, to : str, slot : Slot, kind = Kind.Synchronous):
        self.to = to
        self.slot = slot
        self.kind = kind

    def to_string(self):
        return '{kind} {dest} {fn}'.format(
            kind = self.kind,
            dest = (
                ''
                if self.kind in (Call.Kind.Tail, Call.Kind.Deferred, Call.Kind.Watchdog,)
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
            meta,
        )
    elif leader_type is group_types.Deferred_call:
        return emit_deferred_call(
            body,
            expr,
            state,
            slot,
        )
    elif leader_type is group_types.Watchdog_call:
        return emit_watchdog_call(
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
    elif leader_type is group_types.Enum_ctor_call:
        return emit_enum_ctor_call(
            body,
            expr,
            state,
            slot,
            meta,
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
        if state.what_is_it(str(expr.name.token)) == State.Name_kind.Function:
            if slot is None:
                slot = state.get_slot(name = None, anonymous = True)
            fn_name = str(expr.name.token)
            body.append(Verbatim('function {} {}/{}'.format(
                slot.to_string(),
                state.visible_fns.functions[fn_name]['real_name'],
                state.visible_fns.functions[fn_name]['arity'],
            )))
            return slot

        try:
            evaluated_slot = state.slot_of(str(expr.name.token))
        except KeyError:
            raise exceptions.Unbound_name(None, expr.name.token)
        if must_emit:
            if slot is None:
                slot = state.get_slot(None, anonymous = True)
            body.append(Move.make_copy(
                dest = slot,
                source = evaluated_slot,
            ))
            return slot
        return evaluated_slot
    elif leader_type is group_types.Id:
        if expr.to_string()[0].isupper():
            return emit_function_or_enum_ref(
                body,
                expr,
                state,
                slot,
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
            params = expr.arguments,
        )
        meta.add_function(
            name = str(expr.name.token),
            arity = len(expr.arguments),
            real_name = real_name,
            from_module = meta.prefix,
            params = expr.arguments,
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
    elif leader_type is token_types.Float:
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Ctor(
            'float',
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
        # FIXME Use vector packing to create initialised vectors. It will
        # increase register pressure but will be much more efficient.
        if expr.init:
            init_slot = state.get_slot(None, anonymous = True)
            for each in expr.init:
                init_slot = emit_expr(
                    body = body,
                    expr = each,
                    state = state,
                    slot = init_slot,
                    must_emit = True,
                    meta = meta,
                    toplevel = False,
                )
                body.append(Verbatim('vpush {} {}'.format(
                    slot.to_string(),
                    init_slot.to_string(),
                )))
            state.deallocate_slot(slot = init_slot)

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
    elif leader_type is group_types.Try_expression:
        return emit_try_expr(
            body,
            expr,
            state,
            slot,
            must_emit,
            meta,
        )
    elif leader_type is group_types.Match_expression:
        return emit_match_expr(
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
    elif leader_type is group_types.Pointer_dereference:
        slot = emit_expr(
            body = body,
            expr = expr.value,
            state = state,
            slot = slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        deref_slot = Slot(
            name = slot.name,
            index = slot.index,
            register_set = slot.register_set,
        )
        deref_slot.is_pointer = True
        return deref_slot
    elif leader_type is group_types.Throw_expression:
        emit_throw_expr(
            body = body,
            expr = expr,
            state = state,
        )
        return None
    else:
        raise exceptions.Emitter_exception('expression could not be emitted', expr)


def emit_let(body : list, let_expr, state : State, slot : Slot):
    # Let-bindings always create their own slots.
    name = str(let_expr.name.token)
    if name == IGNORE_VALUE:
        slot = None
    else:
        slot = state.get_slot(name)

    if body and body[-1].to_string():
        body.append(Verbatim(''))
    body.append(Verbatim('; location => {}:{}'.format(
        let_expr.name.token.line + 1,
        let_expr.name.token.character + 1,
    )))
    body.append(Verbatim('; let {} ...'.format(name)))
    emit_expr(
        body = body,
        expr = let_expr.value,
        state = state,
        slot = slot,
        must_emit = False,
        meta = None,
        toplevel = False,
    )
    body.append(Verbatim(''))
    return slot


def emit_throw_expr(body : list, expr, state : State):
    tag_slot = state.get_slot(name = None, anonymous = True)
    exception_slot = state.get_slot(name = None, anonymous = True)

    expr_body = [
        Ctor('atom', tag_slot, repr(str(expr.tag.token))),
    ]
    if expr.value is not None:
        value_slot = emit_expr(
            body = expr_body,
            expr = expr.value,
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        expr_body.append(
            Verbatim('exception {} {} {}'.format(
                exception_slot.to_string(),
                tag_slot.to_string(),
                value_slot.to_string(),
            ))
        )
        state.deallocate_slot(slot = value_slot)
    else:
        expr_body.append(
            Verbatim('exception {} {} void'.format(
                exception_slot.to_string(),
                tag_slot.to_string(),
            ))
        )

    expr_body.append(Verbatim('throw {}'.format(exception_slot.to_string())))

    state.deallocate_slot(slot = exception_slot)
    state.deallocate_slot(slot = tag_slot)

    body.extend(expr_body)

    return None


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
        state.deallocate_slot_if_anonymous(slot)
    elif call_expr.to() == 'echo':
        slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('echo {}'.format(
            slot.to_string()
        )))
        state.deallocate_slot_if_anonymous(slot)
    elif call_expr.to() == 'Std::copy':
        source_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('copy {} {}'.format(
            slot.to_string(),
            source_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(source_slot)
    elif call_expr.to() == 'Std::move':
        # Make the slot anonymous to trigger move semantics.
        moved_from = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Move.make_move(
            source = moved_from,
            dest = slot,
        ))
        slot = slot.become_anonymous()
        state.deallocate_slot(slot = moved_from)
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
        state.deallocate_slot(slot = message_slot)
    elif call_expr.to() == 'Std::Actor::self':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Verbatim('self {}'.format(
            slot.to_string(),
        )))
    elif call_expr.to() == 'Std::Pid::eq':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        lhs_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        rhs_slot = emit_expr(
            body = body,
            expr = args[1],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('pideq {} {} {}'.format(
            slot.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(lhs_slot)
        state.deallocate_slot_if_anonymous(rhs_slot)
    elif call_expr.to() == 'Std::String::to_string':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        source_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('text {} {}'.format(
            slot.to_string(),
            source_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(source_slot)
    elif call_expr.to() == 'Std::String::concat':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        lhs_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        rhs_slot = emit_expr(
            body = body,
            expr = args[1],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('textconcat {} {} {}'.format(
            slot.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(lhs_slot)
        state.deallocate_slot_if_anonymous(rhs_slot)
    elif call_expr.to() == 'Std::String::at':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        string_slot = emit_expr(
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
        body.append(Verbatim('textat {} {} {}'.format(
            slot.to_string(),
            string_slot.to_string(),
            index_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(string_slot)
        state.deallocate_slot_if_anonymous(index_slot)
    elif call_expr.to() == 'Std::String::substr':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        string_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        from_index_slot = emit_expr(
            body = body,
            expr = args[1],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        to_index_slot = emit_expr(
            body = body,
            expr = args[2],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('textsub {} {} {} {}'.format(
            slot.to_string(),
            string_slot.to_string(),
            from_index_slot.to_string(),
            to_index_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(string_slot)
        state.deallocate_slot_if_anonymous(from_index_slot)
        state.deallocate_slot_if_anonymous(to_index_slot)
    elif call_expr.to() == 'Std::String::eq':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        lhs_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        rhs_slot = emit_expr(
            body = body,
            expr = args[1],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('texteq {} {} {}'.format(
            slot.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(lhs_slot)
        state.deallocate_slot_if_anonymous(rhs_slot)
    elif call_expr.to() == 'Std::String::size':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        string_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('textlength {} {}'.format(
            slot.to_string(),
            string_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(string_slot)
    elif call_expr.to() == 'Std::Integer::of_bytes':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        source_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('stoi {} {}'.format(
            slot.to_string(),
            source_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(source_slot)
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
        state.deallocate_slot(slot = value_slot)

        # We don't create or use a slot provided by the caller because we need
        # to return the slot in which the vector resides.
        slot = vector_slot
    elif call_expr.to() == 'Std::Vector::size':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        source_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('vlen {} {}'.format(
            slot.to_string(),
            source_slot.to_string(),
        )))
        state.deallocate_slot_if_anonymous(source_slot)
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

        state.deallocate_slot_if_anonymous(vector_slot)
        state.deallocate_slot_if_anonymous(index_slot)

        slot.is_pointer = True
    elif call_expr.to() == 'Std::Pointer::take':
        expr_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        body.append(Verbatim('ptr {} {}'.format(
            slot.to_string(),
            expr_slot.to_string(),
        )))

        state.deallocate_slot_if_anonymous(expr_slot)

        slot.is_pointer = True
        slot.is_pointer_explicit = True
    elif call_expr.to() == 'Io::read':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        port_slot = emit_expr(
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
        body.append(Verbatim('io_read {} {} {}'.format(
            slot.to_string(),
            port_slot.to_string(),
            value_slot.to_string(),
        )))

        state.deallocate_slot_if_anonymous(port_slot)
        state.deallocate_slot_if_anonymous(value_slot)
    elif call_expr.to() == 'Io::write':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        port_slot = emit_expr(
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
        body.append(Verbatim('io_write {} {} {}'.format(
            slot.to_string(),
            port_slot.to_string(),
            value_slot.to_string(),
        )))

        state.deallocate_slot_if_anonymous(port_slot)
        state.deallocate_slot_if_anonymous(value_slot)
    elif call_expr.to() == 'Io::close':
        if slot is None:
            slot = state.get_slot(None, anonymous = True)
        port_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('io_close {} {}'.format(
            slot.to_string(),
            port_slot.to_string(),
        )))

        state.deallocate_slot_if_anonymous(port_slot)
    elif call_expr.to() == 'Io::wait':
        request_slot = emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        timeout = (args[1] if len(args) >= 2 else token_types.Timeout(INFINITE_DURATION))
        body.append(Verbatim('io_wait {} {} {}'.format(
            Slot.to_address(slot),
            request_slot.to_string(),
            str(timeout.token),
        )))
    elif call_expr.to() == 'Io::cancel':
        emit_expr(
            body = body,
            expr = args[0],
            state = state,
            slot = slot,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        body.append(Verbatim('io_cancel {}'.format(
            slot.to_string(),
        )))
    else:
        raise Exception('unimplemented built-in', call_expr.to())

    return slot

def emit_call(body : list, call_expr, state : State, slot : Slot, meta):
    name = call_expr.name
    args = call_expr.args

    if ((call_expr.to() in BUILTIN_FUNCTIONS) and
            type(call_expr) == group_types.Function_call):
        return emit_builtin_call(body, call_expr, state, slot)

    name_token = None
    if type(name) is group_types.Id:
        name_token = name.name[-1].token
    elif type(name) is group_types.Name_ref:
        name_token = name.name.token
    else:
        name_token = name.token

    fn_name = call_expr.to()
    fn_spec = None
    statically_known = False
    if not state.has_slot(fn_name):
        fn_spec = state.visible_fns.fn_spec(fn_name)
        fn_name = state.visible_fns.real_name(fn_name, token = name_token)
        statically_known = True

    if statically_known:
        if len(args) != fn_spec['arity']:
            raise exceptions.Invalid_number_of_arguments(
                base = name,
                expected = fn_spec['arity'],
                got = len(args),
            )

        params = fn_spec.get('params')

        need_labeled = len(list(filter(
            lambda each: type(each) is token_types.Labeled_parameter_name, params)))
        need_positional = len(list(filter(
            lambda each: type(each) is token_types.Name, params)))

        got_labeled = len(list(filter(
            lambda each: type(each) is group_types.Argument_bind, args)))
        got_positional = len(list(filter(
            lambda each: type(each) is not group_types.Argument_bind, args)))

        if need_positional != got_positional:
            raise exceptions.Invalid_number_of_positional_arguments(
                base = name,
                expected = need_positional,
                got = got_positional,
            )
        if need_labeled != got_labeled:
            raise exceptions.Invalid_number_of_labeled_arguments(
                base = name,
                expected = need_labeled,
                got = got_labeled,
            )

    positional_args = list(filter(
        lambda each: type(each) is not group_types.Argument_bind, args))
    labeled_args = list(filter(
        lambda each: type(each) is group_types.Argument_bind, args))

    applied_args = []
    for each in positional_args:
        tracker = State.Allocation_tracker()
        state.track_slot_allocations(tracker)
        arg_slot = emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        tracker.release(arg_slot, safe = True)
        state.release_tracked_allocations(tracker)
        applied_args.append(arg_slot)

    if (not statically_known) and labeled_args:
        raise Exception('OH NOES: labeled arguments cannot be used if '
            + 'the function called is not known at compile time')
    if labeled_args:
        label_order = list(map(lambda each: str(each.token), filter(
            lambda each: type(each) is token_types.Labeled_parameter_name, fn_spec['params'])))
        labeled_args = dict(map(lambda each: (str(each.name.token), each.expr), labeled_args))
        for each in label_order:
            tracker = State.Allocation_tracker()
            state.track_slot_allocations(tracker)
            arg_slot = emit_expr(
                body = body,
                expr = labeled_args[each],
                state = state,
                slot = None,
                must_emit = False,
                meta = None,
                toplevel = False,
            )
            tracker.release(arg_slot, safe = True)
            state.release_tracked_allocations(tracker)
            applied_args.append(arg_slot)

    body.append(Verbatim('frame %{}'.format(len(args))))
    for i, each in enumerate(applied_args):
        # FIXME if name is None (anonuymous slot) make move not copy
        passer = (Move.make_move if each.is_anonymous() else Move.make_copy)
        body.append(passer(
            dest = Slot(None, i, ARGUMENTS_REGISTER_SET),
            source = each,
        ))
        state.deallocate_slot_if_anonymous(each)

    to = '{}/{}'.format(fn_name, len(args))
    if state.has_slot(fn_name):
        to = state.slot_of(fn_name).to_string()

    call_kind = type(call_expr)
    if call_kind == group_types.Function_call:
        call_kind = Call.Kind.Synchronous
    elif call_kind == group_types.Actor_call:
        call_kind = Call.Kind.Actor
    elif call_kind == group_types.Tail_call:
        call_kind = Call.Kind.Tail
    elif call_kind == group_types.Watchdog_call:
        call_kind = Call.Kind.Watchdog
    else:
        raise Exception('{} cannot be used as a call expression'.format(
            str(type(call_expr))[8:-2],
        ))
    body.append(Call(
        to = to,
        slot = slot,
        kind = call_kind,
    ))

    return slot

def emit_enum_member_id(body : list, expr, state : State, slot : Slot, meta):
    if slot is None:
        slot = state.get_slot(name = None, anonymous = True)

    path, member_name = expr.to_string().rsplit('::', 1)
    if path not in state.visible_fns.enums:
        raise exceptions.Unknown_enum(path, expr)
    body.append(Verbatim('integer {} {}'.format(
        slot.to_string(),
        state.visible_fns.enums[path]['values'][member_name]['n'],
    )))
    return slot

def emit_function_or_enum_ref(body : list, name_expr, state : State, slot : Slot, meta):
    fn_name = name_expr.to_string()

    if slot is None:
        slot = state.get_slot(name = None, anonymous = True)

    path, member_name = fn_name.rsplit('::', 1)
    if path in state.visible_fns.enums:
        if state.visible_fns.enums[path]['is_tag_enum']:
            raise exceptions.Tag_enum_without_ctor_call(path, name_expr)
        emit_enum_member_id(body, name_expr, state, slot, meta)
    else:
        body.append(Verbatim('function {} {}/{}'.format(
            slot.to_string(),
            state.visible_fns.functions[fn_name]['real_name'],
            state.visible_fns.functions[fn_name]['arity'],
        )))
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


def emit_tail_call(body : list, call_expr, state : State, slot : Slot, meta):
    if call_expr.to() in BUILTIN_FUNCTIONS:
        raise Exception('cannot tail call built-in function', call_expr)
    return emit_call(body, call_expr, state, slot, meta)


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


def emit_watchdog_call(body : list, call_expr, state : State, slot : Slot):
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

    body.append(Verbatim('frame %{}'.format(len(args) + 1)))
    for i, each in enumerate(applied_args):
        body.append(Verbatim('copy %{} arguments %{} local'.format(
            i + 1,
            each.index,
        )))

    body.append(Call(
        to = '{}/{}'.format(call_expr.to(), len(args) + 1),
        slot = None,
        kind = Call.Kind.Watchdog,
    ))

    return slot


def emit_operator_call(body : list, call_expr, state : State, slot : Slot):
    name = call_expr.operator
    args = call_expr.args

    # FIXME Emitting arguments and applying the operator to them one-by-one
    # would greatly reduce register pressure. Emitting all arguments first and
    # then applying the operator wastes many registers as they cannot be reused
    # for different arguments.

    applied_args = []
    for i, each in enumerate(args):
        tracker = State.Allocation_tracker()
        state.track_slot_allocations(tracker)
        arg_slot = emit_expr(
            body = body,
            expr = each,
            state = state,
            slot = None,
            must_emit = False,
            meta = None,
            toplevel = False,
        )
        applied_args.append(arg_slot)
        tracker.release(arg_slot, safe = True)
        state.release_tracked_allocations(tracker)

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

    carrying_operators = {
        '+',
        '-',
        '*',
        '/',
        'and',
        'or',
    }

    if str(name.token) == 'not':
        body.append(Verbatim('{} {} {}'.format(
            operator_names[str(name.token)],
            slot.to_string(),
            applied_args[0].to_string(),
        )))
    elif str(name.token) in carrying_operators:
        for i in range(1, len(applied_args)):
            lhs = (applied_args[0] if i == 1 else slot)
            rhs = applied_args[i]

            body.append(Verbatim('{} {} {} {}'.format(
                operator_names[str(name.token)],
                slot.to_string(pointer_dereference = False),
                lhs.to_string(),
                rhs.to_string(),
            )))
            slot.is_pointer = False
    else:
        body.append(Verbatim('{} {} {} {}'.format(
            operator_names[str(name.token)],
            slot.to_string(pointer_dereference = False),
            applied_args[0].to_string(),
            applied_args[1].to_string(),
        )))
        slot.is_pointer = False

    for each in applied_args:
        state.deallocate_slot_if_anonymous(each)

    return slot

def emit_enum_ctor_call(body : list, call_expr, state : State, slot : Slot, meta):
    name = call_expr.name
    value = call_expr.value

    if slot is None:
        slot = state.get_slot(name = None, anonymous = True)

    path, member_name = name.to_string().rsplit('::', 1)
    enum_member = state.visible_fns.enums[path]['values'][member_name]
    enum_member_id = enum_member['n']

    key_slot = state.get_slot(name = None, anonymous = True)
    value_slot = state.get_slot(name = None, anonymous = True)
    expr_body = [
        Ctor('struct', slot, '',),
    ]

    if value is not None:
        expr_body.append(Ctor('atom', key_slot, Ctor.TAG_ENUM_VALUE_FIELD,))
        value_slot = emit_expr(
            body = expr_body,
            expr = value,
            state = state,
            slot = value_slot,
            must_emit = True,
            meta = None,
            toplevel = False,
        )
        expr_body.append(Verbatim('structinsert {} {} {}'.format(
            slot.to_string(),
            key_slot.to_string(),
            value_slot.to_string(),
        )))

    expr_body.extend([
        Ctor('atom', key_slot, Ctor.TAG_ENUM_TAG_FIELD,),
        Ctor('integer', value_slot, enum_member_id,),
        Verbatim('structinsert {} {} {}'.format(
            slot.to_string(),
            key_slot.to_string(),
            value_slot.to_string(),
        )),
    ])
    body.extend(expr_body)

    state.deallocate_slot(slot = value_slot)
    state.deallocate_slot(slot = key_slot)

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
        repr(arms[0]).encode('utf-8') + repr(if_expr).encode('utf-8')
        + repr(state.branches_encountered).encode('utf-8')
    ).hexdigest())
    false_arm_id = 'if_arm_false_{}'.format(hashlib.sha1(
        repr(arms[1]).encode('utf-8') + repr(if_expr).encode('utf-8')
        + repr(state.branches_encountered).encode('utf-8')
    ).hexdigest())
    if_end_id = 'if_end_{}'.format(hashlib.sha1(repr(if_expr).encode('utf-8')).hexdigest())

    # Update the branch counter to give next arms a new value. Without this
    # counter we risk creating two branches with the same name.
    state.branches_encountered += 1

    body.append(Verbatim('if {} {} {}'.format(
        cond_slot.to_string(),
        true_arm_id,
        false_arm_id,
    )))
    state.deallocate_slot_if_anonymous(cond_slot)

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
        state.deallocate_slot(slot = dest)
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

    body.append(Verbatim('; local register pressure = {}'.format(
        state.register_pressure[LOCAL_REGISTER_SET],
    )))
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
    if not len(expr.expressions):
        raise exceptions.Compound_expression_cannot_be_empty(
            exceptions.Compound_expression_cannot_be_empty.MESSAGE,
            expr,
        )

    tracker = State.Allocation_tracker()
    state.track_slot_allocations(tracker)
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
    value_slot = emit_expr(
        body = body,
        expr = expr.expressions[-1],
        state = state,
        slot = slot,
        must_emit = must_emit,
        meta = meta,
        toplevel = False,
    )

    # Release the value slot as we do not want to deallocate the value we are
    # about to return. Safe release is needed because the slot may have been
    # allocated before we started tracking.
    tracker.release(value_slot, safe = True)
    state.release_tracked_allocations(tracker)

    return value_slot


def emit_try_expr(body : list, expr, state : State, slot : Slot = None, must_emit = False, meta = None):
    expression = expr.expr
    handlers = expr.handling_blocks

    expr_block_name = 'try_{}'.format(hashlib.sha1(
        repr(expression).encode('utf-8')
        + repr(expr).encode('utf-8')
        + repr(id(expression)).encode('utf-8')
    ).hexdigest())
    expr_body = [
        Verbatim('enter .block: {}'.format(expr_block_name)),
    ]
    slot = emit_expr(
        body = expr_body,
        expr = expression,
        state = state,
        slot = slot,
        must_emit = must_emit,
        meta = meta,
        toplevel = False,
    )
    expr_body.append(Verbatim('leave'))
    expr_body.append(Verbatim('.end'))

    handler_bodies = []
    for each in handlers:
        tag_name = str(each.tag.tag.token)

        handler_block_name = 'catch_{}'.format(hashlib.sha1(
            repr(expression).encode('utf-8')
            + repr(each).encode('utf-8')
            + repr(id(each)).encode('utf-8')
        ).hexdigest())
        handler_body = [
            Verbatim('catch "{}" .block: {}'.format(
                tag_name,
                handler_block_name
            ))
        ]

        exception_variable_name = str(each.name.token)
        name_slot = None
        if exception_variable_name == '_':
            exception_variable_slot = state.get_slot(None, anonymous = True)
            handler_body.append(Verbatim('draw {}'.format(
                exception_variable_slot.to_string(),
            )))
            handler_body.append(Verbatim('delete {}'.format(
                exception_variable_slot.to_string(),
            )))
            state.deallocate_slot(slot = exception_variable_slot)
        else:
            name_slot = state.get_slot(exception_variable_name)
            handler_body.append(Verbatim('draw {}'.format(
                name_slot.to_string(),
            )))
            handler_body.append(Verbatim('exception_value {ex} {ex}'.format(
                ex = name_slot.to_string(),
            )))

        tracker = State.Allocation_tracker()
        state.track_slot_allocations(tracker)
        emit_expr(
            body = handler_body,
            expr = each.expr,
            state = state,
            slot = slot,
            must_emit = must_emit,
            meta = meta,
            toplevel = False,
        )
        state.release_tracked_allocations(tracker)

        if name_slot is not None:
            state.deallocate_slot(slot = name_slot)

        handler_body.append(Verbatim('leave'))
        handler_body.append(Verbatim('.end'))

        handler_bodies.append(handler_body)

    body.append(Verbatim('try'))
    for each in handler_bodies:
        body.extend(each)
    body.extend(expr_body)

    return slot


def emit_match_enum_expr(body : list, expr, state : State, slot : Slot = None,
        must_emit = False, meta = None):
    handlers = expr.handling_blocks
    expression = expr.expr

    expr_block_name = 'match_{}'.format(hashlib.sha1(
        repr(expression).encode('utf-8')
        + repr(expr).encode('utf-8')
        + repr(id(expression)).encode('utf-8')
    ).hexdigest())
    expr_body = [
        Verbatim('; match ... (with ...)'.format(expr_block_name)),
    ]

    # First, we emit the expression whose result is to be matched to patterns of
    # with expressions. It gets its own slot as its result will never be
    # returned to the parent expression (if any). This slot may be deallocated
    # after we emitted the whole match-expression.
    checked_expr_slot = emit_expr(
        body = expr_body,
        expr = expression,
        state = state,
        slot = state.get_slot(name = None, anonymous = True),
        must_emit = must_emit,
        meta = meta,
        toplevel = False,
    )
    expr_body.append(Verbatim('; matching expr of {} to withs'.format(expr_block_name)))

    # Then, we determine the name of the enum that is matched by this
    # expression. We have to do this because we need to know if this is a tag
    # enum, as in case of tag enums two additional slots are needed: one for the
    # tag, and one for the value.
    enum_name = handlers[0].pattern.to_string().rsplit('::', 1)[0]
    is_tag_enum = state.visible_fns.enums[enum_name]['is_tag_enum']
    handlers_extract_value = any(each.name is not None for each in handlers)

    # If this is a tag enum then we need to extract its tag. After that it is
    # simple integer comparisons, but since tag enums may carry a value we have
    # to deconstruct them.
    enum_tag_slot = None
    if is_tag_enum:
        tmp_slot = state.get_slot(name = None, anonymous = True)
        enum_tag_slot = state.get_slot(name = None, anonymous = True)
        expr_body.extend([
            Ctor('atom', tmp_slot, Ctor.TAG_ENUM_TAG_FIELD),
            Verbatim('structat {enum_tag_slot} {slot} {tmp}'.format(
                enum_tag_slot = enum_tag_slot.to_string(),
                slot = checked_expr_slot.to_string(),
                tmp = tmp_slot.to_string(),
            )),
            Move.make_copy(enum_tag_slot.as_pointer(), enum_tag_slot),
        ])
        state.deallocate_slot(slot = tmp_slot)

    body.extend(expr_body)

    # Then, let's create markers for with-expressions. We need two markers for
    # each expression - one for a match, and one for a non-match. Why? Because
    # the if instruction that actually implements the comparisons has two
    # targets, so we emit a marker for both of them.
    match_done_marker = '{}_done'.format(expr_block_name)
    with_expr_markers = []
    for i, each in enumerate(handlers):
        s = (repr(each.pattern) + repr(each.name) + repr(each.expr))
        with_block_name = '{}_with_{}'.format(
            expr_block_name,
            hashlib.sha1(
                s.encode('utf-8')
                + s.encode('utf-8')
                + repr(id(each.pattern) + id(each.name) + id(each.expr)).encode('utf-8')
            ).hexdigest())
        with_expr_markers.append((
            (with_block_name + '_true'),
            (with_block_name + '_false'),
        ))

    # Then, we emit the actual comparison code. It is a simple sequence of ifs
    # that try to match the match-condition-expression's value to each
    # with-expression tag in sequence.
    tag_check_slot = state.get_slot(name = None, anonymous = True)
    for i, each in enumerate(handlers):
        tag_check_body = []

        if type(each.pattern) == group_types.Name_ref and each.pattern.name.token == '_':
            tag_check_body = [
                Verbatim('; jump to the catch-all for {}'.format(
                    expr_block_name,
                )),
                Verbatim('jump {}'.format(
                    with_expr_markers[i][0],
                )),
            ]
            body.extend(tag_check_body)
            break

        emit_enum_member_id(
            tag_check_body,
            each.pattern,
            state,
            tag_check_slot,
            meta)
        tag_check_body.extend([
            Verbatim('eq {tag_check} {tag_check} {enum_tag}'.format(
                tag_check = tag_check_slot.to_string(),
                enum_tag = enum_tag_slot.to_string(),
            )),
            Verbatim('if {tag_check} {tag_check_true} {tag_check_false}'.format(
                tag_check = tag_check_slot.to_string(),
                tag_check_true = with_expr_markers[i][0],
                tag_check_false = with_expr_markers[i][1],
            )),
            Verbatim('.mark: {}'.format(
                with_expr_markers[i][1],
            )),
        ])
        body.extend(tag_check_body)
    state.deallocate_slot(slot = tag_check_slot)

    # As the last step, let's emit the actual with-expressions that the overall
    # match-expression should evaluate to.
    body.append(Verbatim('; handling withs of {}'.format(expr_block_name)))
    for i, each in enumerate(handlers):
        with_expr_body = [
            Verbatim('.mark: {}'.format(with_expr_markers[i][0])),
        ]

        extracted_name = (str(each.name.token) if each.name is not None else None)
        if extracted_name:
            value_slot = state.get_slot(name = extracted_name)
            tmp_slot = state.get_slot(name = None, anonymous = True)
            with_expr_body.extend([
                Verbatim(
                    '; location => {}:{}'.format(
                        each.name.token.line + 1,
                        each.name.token.character + 1,)),
                Verbatim(
                    '; extracting value named {}...'.format(
                        repr(extracted_name))),
                Ctor('atom', tmp_slot, Ctor.TAG_ENUM_VALUE_FIELD),
                Verbatim('structat {value_slot} {checked_slot} {tmp}'.format(
                    value_slot = value_slot.to_string(),
                    checked_slot = checked_expr_slot.to_string(),
                    tmp = tmp_slot.to_string(),
                )),
                Move.make_copy(value_slot.as_pointer(), value_slot),
                Verbatim('; extracted value'),
            ])
            state.deallocate_slot(slot = tmp_slot)
        slot = emit_expr(
            body = with_expr_body,
            expr = each.expr,
            state = state,
            slot = slot,
            must_emit = True,
            meta = meta,
            toplevel = False,
        )
        if extracted_name:
            state.deallocate_slot(name = extracted_name)

        if i < (len(handlers) - 1):
            with_expr_body.append(Verbatim('jump {}'.format(match_done_marker)))

        if type(each.pattern) == group_types.Name_ref and each.pattern.name.token == '_':
            body.append(
                Verbatim('; this is the catch-all for {}'.format(
                    expr_block_name,
                )),
            )

        body.extend(with_expr_body)

    body.append(Verbatim('; end of {}'.format(expr_block_name)))
    body.append(Verbatim('.mark: {}'.format(match_done_marker)))

    if is_tag_enum:
        state.deallocate_slot(slot = enum_tag_slot)
    state.deallocate_slot(slot = checked_expr_slot)

    return slot

def emit_match_integer_expr(body : list, expr, state : State, slot : Slot = None,
        must_emit = False, meta = None):
    handlers = expr.handling_blocks
    expression = expr.expr
    expr_block_name = 'match_{}'.format(hashlib.sha1(
        repr(expression).encode('utf-8')
        + repr(expr).encode('utf-8')
        + repr(id(expression)).encode('utf-8')
    ).hexdigest())
    expr_body = []
    slot = emit_expr(
        body = expr_body,
        expr = expression,
        state = state,
        slot = slot,
        must_emit = must_emit,
        meta = meta,
        toplevel = False,
    )
    match_slot = slot
    expr_body.append(Verbatim('; matching expr of {} to withs'.format(expr_block_name)))

    body.extend(expr_body)

    with_expr_markers = []
    for i, each in enumerate(handlers):
        s = (repr(each.pattern) + repr(each.name) + repr(each.expr))
        with_block_name = '{}_with_{}'.format(
            expr_block_name,
            hashlib.sha1(
                s.encode('utf-8')
                + s.encode('utf-8')
                + repr(id(each.pattern) + id(each.name) + id(each.expr)).encode('utf-8')
            ).hexdigest())
        with_expr_markers.append((
            (with_block_name + '_true'),
            (with_block_name + '_false'),
        ))

    match_done_marker = '{}_done'.format(expr_block_name)

    with_expr_slot = state.get_slot(name = None, anonymous = True)

    for i, each in enumerate(handlers):
        with_expr_body = []

        if type(each.pattern) == group_types.Name_ref and each.pattern.name.token == '_':
            with_expr_body = [
                Verbatim('; jump to the catch-all for {}'.format(
                    expr_block_name,
                )),
                Verbatim('jump {}'.format(
                    with_expr_markers[i],
                )),
            ]
            body.extend(with_expr_body)
            break

        with_expr_slot = emit_expr(
            with_expr_body,
            each.pattern,
            state,
            with_expr_slot,
            meta)
        with_expr_body.extend([
            Verbatim('eq {we} {we} {me}'.format(
                we = with_expr_slot.to_string(),
                me = match_slot.to_string(),
            )),
            Verbatim('if {we} {with_expr_true} {with_expr_false}'.format(
                we = with_expr_slot.to_string(),
                with_expr_true = with_expr_markers[i][0],
                with_expr_false = with_expr_markers[i][1],
            )),
            Verbatim('.mark: {}'.format(
                with_expr_markers[i][1],
            )),
        ])
        body.extend(with_expr_body)

    body.append(Verbatim('; handling withs of {}'.format(expr_block_name)))
    for i, each in enumerate(handlers):
        with_expr_body = [
            Verbatim('.mark: {}'.format(with_expr_markers[i][0])),
        ]
        with_expr_slot = emit_expr(
            body = with_expr_body,
            expr = each.expr,
            state = state,
            slot = with_expr_slot,
            must_emit = True,
            meta = meta,
            toplevel = False,
        )

        if i < (len(handlers) - 1):
            with_expr_body.append(Verbatim('jump {}'.format(match_done_marker)))

        if type(each.pattern) == group_types.Name_ref and each.pattern.name.token == '_':
            body.append(
                Verbatim('; this is the catch-all for {}'.format(
                    expr_block_name,
                )),
            )

        body.extend(with_expr_body)

    body.append(Verbatim('; end of {}'.format(expr_block_name)))
    body.append(Verbatim('.mark: {}'.format(match_done_marker)))

    return with_expr_slot

def emit_match_expr(body : list, expr, state : State, slot : Slot = None, must_emit = False, meta = None):
    # Check if the match expression is consistent with regards to values it
    # checks. Match expressions in Viuact only work on values of the same type;
    # only on integers, strings, or members of the same enum. If they are mixed
    # and matched we should throw an error.
    handlers = expr.handling_blocks
    if not handlers:
        raise exceptions.Match_without_with_expressions(expr)

    MATCH_KIND_ENUM = 0
    MATCH_KIND_INTEGER = 1
    MATCH_KIND_STRING = 1

    match_kind = None
    if type(handlers[0].pattern) == group_types.Id:
        match_kind = MATCH_KIND_ENUM

        path, field = handlers[0].pattern.to_string().rsplit('::', 1)
        matched_enum = state.visible_fns.enums[path]
        checked_fields = []
        has_catchall = False
        for each in handlers:
            pat = each.pattern
            if type(pat) == group_types.Name_ref and pat.name.token == '_':
                has_catchall = True

                if each.name is not None:
                    raise exceptions.Catchall_with_cannot_bind(expr)

                continue

            each_path, each_field = pat.to_string().rsplit('::', 1)
            if each_path != path:
                raise exceptions.Mismatched_enums(expr, path, each_path)
            if each_field not in matched_enum['values']:
                raise exceptions.Enum_field_does_not_exist(
                    expr, path, each_field)
            if each.name and not matched_enum['values'][each_field]['tag']:
                raise exceptions.Non_tag_field_cannot_bind(
                    expr, path, each_field)
            checked_fields.append(each_field)

        checked_fields = set(checked_fields)
        for each in sorted(matched_enum['values'].keys()):
            if each not in checked_fields and not has_catchall:
                raise exceptions.Enum_field_not_checked_for(expr, path, each)
    elif type(handlers[0].pattern) == token_types.Integer:
        match_kind = MATCH_KIND_INTEGER

        has_catchall = False
        for each in handlers:
            pat = each.pattern
            if type(pat) == group_types.Name_ref and pat.name.token == '_':
                has_catchall = True

                if each.name is not None:
                    raise exceptions.Catchall_with_cannot_bind(expr)

                continue

            if each.name is not None:
                raise exceptions.Match_over_integers_cannot_bind(expr)

        if not has_catchall:
            raise exceptions.Match_over_integers_must_have_a_catchall(expr)
    else:
        raise exceptions.Invalid_type_for_match(expr, handlers[0].pattern)

    if match_kind == MATCH_KIND_ENUM:
        return emit_match_enum_expr(body, expr, state, slot, must_emit, meta)
    elif match_kind == MATCH_KIND_INTEGER:
        return emit_match_integer_expr(body, expr, state, slot, must_emit, meta)

def resolve_field_access(expr):
    base_expr, fields = None, []

    if type(expr[1]) is list and type(expr[1][0]) is token_types.Dot:
        base_expr, fields = resolve_field_access(expr[1])
        fields.append(expr[2])
    else:
        base_expr = expr[1]
        fields = [expr[2]]

    return (base_expr, fields)

def emit_field_assignment(body : list, expr, state : State, slot : Slot):
    slot = emit_expr(
        body = body,
        expr = expr.value,
        state = state,
        slot = slot,
    )

    field = expr.field

    base_expr, fields = resolve_field_access(field)

    base_target_slot = None
    if type(base_expr) is token_types.Name:
        base_target_slot = state.slot_of(str(base_expr.token))
    else:
        base_target_slot = emit_expr(
            body = body,
            expr = base_expr,
            state = state,
            slot = None,
        )

    field_name_slot = state.get_slot(None, anonymous = True)
    field_names = list(filter(lambda each: str(each.token) != '.', fields))

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

    if inner_struct_slot:
        state.deallocate_slot(slot = inner_struct_slot)
    state.deallocate_slot(slot = field_name_slot)

    # FIXME Figure out what to do if we want struct field updates to return values.
    # body.append(Verbatim('structat {} {} {}'.format(
    #     slot.to_string(),
    #     base_target_slot.to_string(inner_struct_slot is not None),
    #     field_name_slot.to_string(),
    # )))

    return slot

def emit_struct_field_access(body : list, expr, state : State, slot : Slot, must_emit = False, meta = None):
    field = expr.name

    base_expr, fields = resolve_field_access(field)

    base_source_slot = None
    if type(base_expr) in (token_types.Module_name, token_types.Name,):
        base_source_slot = state.slot_of(str(base_expr.token))
    else:
        base_source_slot = emit_expr(
            body = body,
            expr = base_expr,
            state = state,
            slot = None,
        )

    field_name_slot = state.get_slot(None, anonymous = True)
    field_names = list(filter(lambda each: str(each.token) != '.', fields))

    if slot is None:
        slot = state.get_slot(None, anonymous = True)

    for i, field_name in enumerate(field_names):
        body.append(Verbatim('atom {} {}'.format(
            field_name_slot.to_string(),
            repr(field_name.token),
        )))
        body.append(Verbatim('structat {} {} {}'.format(
            slot.to_string(),
            base_source_slot.to_string(),
            field_name_slot.to_string(),
        )))
        base_source_slot = slot

    state.deallocate_slot(slot = field_name_slot)

    slot.is_pointer = True
    return slot
