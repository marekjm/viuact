import enum
import hashlib
import os

import viuact.util.log
import viuact.forms


EXEC_MODULE = '<main>'

BUILTIN_FUNCTIONS = (
    'print',
)


def typeof(value):
    return str(type(value))[8:-2]


class Type:
    class t:
        def __init__(self, name, parameters = ()):
            self._name = name               # str
            self._parameters = parameters   # [Type]

        def __eq__(self, other):
            if type(other) is not Type.t:
                raise TypeError('cannot compare type with {}'.format(typeof(other)))
            n = (str(self.name()) == str(other.name()))
            p = (self.parameters() == other.parameters())
            return (n and p)

        def __str__(self):
            if self._parameters:
                return '(({}) {})'.format(
                    ' '.join(map(str, self.parameters())),
                    str(self.name()),
                )
            else:
                return str(self.name())

        def name(self):
            return self._name

        def parameters(self):
            return self._parameters

        def polymorphic(self):
            n = self.name().startswith("'")
            p = any(map(lambda x: x.polymorhpic(), self.parameters()))
            return (n or p)

        def merge(self, other):
            raise None

        def match(self, other, template_parameters):
            tp = template_parameters

            if self.polymorphic() and tp[self.name()] is None:
                tp[self.name()] = other
                return True, tp

            if self.polymorphic() and tp[self.name()] is not None:
                return tp[self.name()].match(other, template_parameters)

            if self.name() != other.name():
                return False, tp

            for i, pair in zip(self.parameters(), other.parameters()):
                a, b = pair
                ok, _ = a.match(b, tp)
                if not ok:
                    return False, tp

            return True, tp

    class i8(t):
        def __init__(self):
            super().__init__('i8')

    class i16(t):
        def __init__(self):
            super().__init__('i16')

    class i32(t):
        def __init__(self):
            super().__init__('i32')

    class i64(t):
        def __init__(self):
            super().__init__('i64')

    class u8(t):
        def __init__(self):
            super().__init__('u8')

    class u16(t):
        def __init__(self):
            super().__init__('u16')

    class u32(t):
        def __init__(self):
            super().__init__('u32')

    class u64(t):
        def __init__(self):
            super().__init__('u64')

    class string(t):
        def __init__(self):
            super().__init__('string')


class Module_info:
    def __init__(self, name, source_file):
        self._name = name
        self._source_file = source_file

        self._functions = {}
        self._function_signatures = {}

    def name(self):
        return self._name

    def make_fn(self, name, parameters):
        n = '{}/{}'.format(name, len(parameters))
        if n not in self._function_signatures:
            viuact.util.log.raw(n, list(self._function_signatures.keys()))
            raise viuact.errors.No_signature_for_function(
                pos = name.tok().at(),
                fn = n,
            )

        self._functions[n] = {
            'local': True,
            'from': (None, None,),  # module name, containing file
            'parameters': parameters,
            'base_name': str(name),
            'arity': len(parameters),
        }
        viuact.util.log.print('module info [{}]: visible local fn {}'.format(
            self._name,
            n,
        ))
        return self

    def make_fn_signature(self, name, parameters, return_type, template_parameters):
        n = '{}/{}'.format(str(name), len(parameters))
        self._function_signatures[n] = {
            'parameters': parameters,
            'base_name': str(name),
            'arity': len(parameters),
            'return': return_type,
            'template_parameters': template_parameters,
        }
        viuact.util.log.print('module info [{}]: local fn sig {}'.format(
            self._name,
            n,
        ))
        return self

    def signature(self, fn_name):
        return self._function_signatures[fn_name]

    def fns(self, local = None, imported = None):
        res = []
        for k, v in self._functions.items():
            if (local is None) or (local is True and v['local']):
                res.append((k, v,))
                continue
            if (imported is None) or (imported is True and not v['local']):
                res.append((k, v,))
                continue
        return res


class Register_set(enum.Enum):
    LOCAL = 'local'
    PARAMETERS = 'parameters'
    ARGUMENTS = 'arguments'
    VOID = 'void'
    DEFAULT = LOCAL

class Slot:
    IGNORE = '_'

    def __init__(self, name, index, register_set = Register_set.DEFAULT):
        self.name = name
        self.index = index
        self.register_set = register_set

        self._is_pointer = False

    def __eq__(self, other):
        if type(other) is not Slot:
            raise TypeError('cannot compare Slot to {}'.format(
                other.__class__.__name__))
        return ((self.index == other.index)
            and (self.register_set == other.register_set))

    @staticmethod
    def make_void():
        return Slot(
            name = Slot.IGNORE,
            index = None,
            register_set = Register_set.VOID,
        )

    @staticmethod
    def make_anonymous(index, register_set = Register_set.DEFAULT):
        return Slot(
            name = None,
            index = index,
            register_set = register_set,
        )

    def is_void(self):
        return (self.register_set == Register_set.VOID)

    def is_anonymous(self):
        return (self.name is None)

    def is_pointer(self):
        return self._is_pointer

    def as_pointer(self, pointer = True):
        s = Slot(self.name, self.index, self.register_set)
        s._is_pointer = pointer
        return s

    def to_string(self):
        if self.is_void():
            return 'void'
        return '{}{} {}'.format(
            ('*' if self.is_pointer() else '%'),
            self.index,
            self.register_set.value,
        )

class Scope:
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        return self.state

    def __exit__(self, *args):
        self.state.erase()
        self.state._parent._active = True

class State:
    def __init__(self, fn, upper = None, parent = None):
        self._fn = fn           # Name of the function for which this state was
                                # created.
        self._special = 0       # General purpose counter for special events.

        self._upper = upper     # Used for closures.
        self._parent = parent   # Parent scope, e.g. for function call
                                # arguments.
        self._next_slot_index = {
            Register_set.LOCAL: 1,
        }
        self._named_slots = {}
        self._allocated_slots = []
        self._freed_slots = []
        self._cancelled_slots = []

        self._types = {}

        # State is active it represents the innermost scope of the currently
        # compiled function. Only active state may be mutated, i.e. it is an
        # error to allocate, deallocate, cancel, etc. slots in an inactive
        # state.
        self._active = True

        if parent is not None:
            for k, v in self._parent._next_slot_index.items():
                self._next_slot_index[k] = v

    def assert_active(self, wanted = True):
        if (self._active != wanted):
            raise viuact.errors.Mutation_of_inactive_state()

    def as_active(self, fn, *args, **kwargs):
        a = self._active
        self._active = True
        result = fn(self, *args, **kwargs)
        self._active = a
        return result

    def push_pressure(self, register_set):
        if self._parent is None:
            return
        n = self._next_slot_index[register_set]
        p = self._parent._next_slot_index[register_set]
        self._parent._next_slot_index[register_set] = max(n, p)
        self._parent.push_pressure(register_set)

    def push_deallocations(self):
        if self._parent is None:
            return

        self._parent._cancelled_slots.extend(self._cancelled_slots)
        self._cancelled_slots.clear()

        self._parent._freed_slots.extend(self._freed_slots)
        self._freed_slots.clear()

        self._parent.push_deallocations()

    def deallocate_slot(self, slot):
        self.assert_active()
        if slot.is_void():
            return

        # viuact.util.log.note('dealloc: {} [top = {}]'.format(
        #     slot.to_string(),
        #     self._next_slot_index[slot.register_set],
        # ))

        try:
            self._allocated_slots.remove((slot.index, slot.register_set,))
            if slot.name in self._named_slots:
                del self._named_slots[slot.name]
            self.remove_type(slot)
            self._freed_slots.append(slot)
        except ValueError:
            if self._parent:
                self._parent.as_active(State.deallocate_slot, slot)
            else:
                raise
        # viuact.util.log.note('  freed slot: {}'.format(slot.to_string()))
        return self

    def cancel_slot(self, slot):
        self.assert_active()
        if slot.is_void():
            return

        # viuact.util.log.note('cancel: {} [top = {}]'.format(
        #     slot.to_string(),
        #     self._next_slot_index[slot.register_set],
        # ))

        try:
            self._allocated_slots.remove((slot.index, slot.register_set,))
            if slot.name in self._named_slots:
                del self._named_slots[slot.name]
            self._cancelled_slots.append(slot)
        except ValueError:
            if self._parent:
                self._parent.as_active(State.cancel_slot, slot)
            else:
                raise
        return self

    def find_free_slot(self, register_set):
        for each in self._cancelled_slots:
            if each.register_set == register_set:
                # viuact.util.log.note('reusing cancelled slot {}'.format(each.to_string()))
                self._cancelled_slots.remove(each)
                return each
        for each in self._freed_slots:
            if each.register_set == register_set:
                # viuact.util.log.note('reusing dealloced slot {}'.format(each.to_string()))
                self._freed_slots.remove(each)
                return each
        if self._parent is not None:
            return self._parent.find_free_slot(register_set)
        return None

    def insert_allocated(self, slot):
        self.assert_active()
        self._allocated_slots.append( (slot.index, slot.register_set,) )
        return self

    def allocate_slot(self, register_set):
        self.assert_active()
        found_freed = self.find_free_slot(register_set)
        i = None
        if found_freed is None:
            i = self._next_slot_index[register_set]
            self._next_slot_index[register_set] += 1
            self.push_pressure(register_set)
        else:
            i = found_freed.index
        self._allocated_slots.append( (i, register_set,) )
        return i

    def get_slot(self, name, register_set = Register_set.DEFAULT):
        self.assert_active()
        if name is not None and type(name) is not str:
            raise TypeError('cannot use {} to name a slot'.format(
                typeof(name),
            ))

        slot = Slot(
            name,
            self.allocate_slot(register_set),
            register_set,
        )

        # Use None as name to create anonymous slots.
        if name is not None:
            # viuact.util.log.print('defined slot: {} = {}'.format(slot.to_string(), name))
            self._named_slots[name] = slot

        return slot

    def slot_of(self, name):
        try:
            return self._named_slots[name]
        except KeyError:
            if self._parent is None:
                raise
            return self._parent.slot_of(name)

    def actual_pressure(self, register_set):
        n = self._next_slot_index[register_set]
        a = self._allocated_slots
        f = list(filter(
            lambda i: i.register_set == register_set, self._freed_slots))

        # viuact.util.log.raw('a:', a)
        # viuact.util.log.raw('f:', list(map(lambda x: x.index, f)))

        a = (max(list(map(lambda x: x[0], a))) if a else None)
        f = (max(list(map(lambda x: x.index, f))) if f else None)

        # viuact.util.log.raw('pressure.n:', n)
        # viuact.util.log.raw('pressure.a:', a)
        # viuact.util.log.raw('pressure.f:', f)

        if a is not None:
            a = (a + 1)
        if f is not None:
            f = (f + 1)

        # By default, use the pressure from the next slot as this is exactly the
        # number we should use in the most pessimistic case.
        pressure = n

        # However, if we have information about allocations let's just use the
        # maximum index of allocated slots. This will be more accurate and we
        # will not waste registers.
        if a is not None:
            pressure = a

        # To get an even better value for the actual pressure, let's consult the
        # deallocated registers (if any). If a register was deallocated it must
        # have been used at some point so its index should be taken into
        # account.
        #
        # BEWARE, though! Instead of blindly overwriting the pressure value we
        # should take a max() from freed and allocated indexes. It is possible
        # that the slot with the maximum index was not deallocated until the end
        # of the function.
        if f is not None:
            pressure = max(f, (a or 0))

        # viuact.util.log.raw('pressure.x:', pressure)

        return pressure

    def scoped(self):
        self._active = False
        s = State(fn = self.fn(), parent = self)
        return Scope(s)

    def erase(self):
        self.assert_active()
        for each in self._allocated_slots:
            i, r = each
            self.deallocate_slot(Slot(
                name = None,
                index = i,
                register_set = r,
            ))
        self.push_deallocations()

    def fn(self):
        return self._fn

    def special(self):
        n = self._special
        self._special += 1
        return n

    def _set_type_of(self, slot, t):
        if type(slot) is not Slot:
            raise TypeError('cannot get type of non-slot {}: {}'.format(
                typeof(slot),
                slot,
            ))
        if slot.is_void():
            raise TypeError('cannot get type of void slot')
        key = slot.to_string()
        if (slot.index, slot.register_set,) not in self._allocated_slots:
            viuact.util.log.raw('{} not in scope: {}'.format(key,
                str(self._allocated_slots)))
            raise KeyError(slot.to_string())
        viuact.util.log.raw('type-of: {} <- {}'.format(key, t))
        self._types[key] = t
        return t

    def _get_type_of(self, slot):
        if type(slot) is not Slot:
            raise TypeError('cannot get type of non-slot {}: {}'.format(
                typeof(slot),
                slot,
            ))
        if slot.is_void():
            raise TypeError('cannot get type of void slot')
        key = slot.to_string()
        if (slot.index, slot.register_set,) not in self._allocated_slots:
            viuact.util.log.raw('{} not in scope: {}'.format(key,
                str(self._allocated_slots)))
            raise KeyError(slot.to_string())
        viuact.util.log.raw('{} {}'.format(key, list(map(str, self._types.keys()))))
        t = self._types[key]
        viuact.util.log.raw('type-of: {} -> {}'.format(key, t))
        return t

    def type_of(self, slot, t = None):
        try:
            if t is None:
                return self._get_type_of(slot)
            else:
                return self._set_type_of(slot, t)
        except KeyError:
            if self._parent:
                return self._parent.type_of(slot, t)
            else:
                raise

    def remove_type(self, slot):
        self.assert_active()
        if type(slot) is str:
            del self._types[slot]
        elif type(slot) is Slot:
            if slot.is_void():
                raise None
            key = None
            if slot.is_anonymous():
                key = slot.to_string()
            else:
                key = slot.name
            del self._types[key]
        else:
            raise None


class Fn_cc:
    def __init__(self, name):
        self.name = name
        self.body = []

    def append(self, line):
        self.body.append(line)
        return self

class CC_out:
    def __init__(self, main):
        self.main = main
        self.nested = {}


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
            raise TypeError('{} cannot be used as Slot'.format(
                source.__class__.__name__))
        if source.is_void():
            raise viuact.errors.Source_cannot_be_void(
                (0, 0), '{} to {}'.format(of_type, dest.to_string()))

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
        return '{kind}{dest} {fn}'.format(
            kind = self.kind,
            dest = (
                ''
                if self.kind in (Call.Kind.Tail, Call.Kind.Deferred, Call.Kind.Watchdog,)
                else (' ' + self.slot.to_string())
            ),
            fn = self.to,
        )


def emit_builtin_call(mod, body, st, result, form):
    if str(form.to().name()) == 'print':
        if len(form.arguments()) != 1:
            raise viuact.errors.Invalid_arity(
                form.to().name().tok().at(),
                expected = 1,
                got = len(form.arguments()),
            )
        with st.scoped() as sc:
            slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = (sc.get_slot(None) if result.is_void() else result),
                expr = form.arguments()[0],
            )
            body.append(Verbatim('print {}'.format(
                slot.to_string(),
            )))
            body.append(Verbatim(''))

        return slot

def emit_fn_call(mod, body, st, result, form):
    if str(form.to().name()) in BUILTIN_FUNCTIONS:
        return emit_builtin_call(mod, body, st, result, form)

    base_name = str(form.to().name().tok())
    called_fn_name = '{name}/{arity}'.format(
        name = base_name,
        arity = len(form.arguments()),
    )

    candidates = list(filter(
        lambda each: each[1]['base_name'] == base_name,
        mod.fns(),
    ))
    if not candidates:
        raise viuact.errors.Unknown_function(
            form.to().name().tok().at(),
            called_fn_name,
        )

    signature = (lambda x: (x[0] if x else None))(list(filter(
        lambda each: each[1]['arity'] == len(form.arguments()),
        candidates
    )))
    if signature is None:
        e = viuact.errors.Invalid_arity(
            form.to().name().tok().at(),
            called_fn_name,
        )
        for each in candidates:
            e.note('candidate: {}({})'.format(
                each[1]['base_name'],
                ' '.join(map(lambda p: str(p.name()), each[1]['parameters'])),
            ))
        raise e

    viuact.util.log.raw('call to {}: signature = {}'.format(
        called_fn_name,
        signature,
    ))
    type_signature = mod.signature(called_fn_name)
    viuact.util.log.raw('call to {}: type sig =  {}'.format(
        called_fn_name,
        type_signature,
    ))

    args = []
    if True:
        parameters = signature[1]['parameters']
        arguments = form.arguments()

        need_labelled = list(filter(
            lambda a: type(a) is viuact.forms.Labelled_parameter,
            parameters))
        need_positional = list(filter(
            lambda a: type(a) is viuact.forms.Named_parameter, parameters))

        got_labelled = dict(
            map(lambda a: ( str(a.name()), a.val(), ),
            filter(lambda a: type(a) is viuact.forms.Argument_bind,
            arguments)))
        got_positional = list(filter(
            lambda a: type(a) is not viuact.forms.Argument_bind, arguments))

        # print('positional:', need_positional, '=>', got_positional)
        # print('labelled:',
        #     list(map(lambda a: str(a.name()), need_labelled)),
        #     '=>', got_labelled)

        if len(got_positional) < len(need_positional):
            raise viuact.errors.Missing_positional_argument(
                form.to().name().tok().at(),
                called_fn_name,
                need_positional[len(got_positional)],
            )
        for l in need_labelled:
            if str(l.name()) not in got_labelled:
                raise viuact.errors.Missing_labelled_argument(
                    form.to().name().tok().at(),
                    called_fn_name,
                    l,
                )

        args = got_positional[:]
        for a in need_labelled:
            args.append(got_labelled[str(a.name())])

    body.append(Verbatim('frame %{} arguments'.format(len(form.arguments()))))

    template_parameters = { x.name() : None for x in
            type_signature['template_parameters'] }
    for i, arg in enumerate(args):
        body.append(Verbatim('; for argument {}'.format(i)))
        slot = st.get_slot(name = None)
        with st.scoped() as sc:
            slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = slot,
                expr = arg,
            )
            body.append(Move.make_move(
                source = slot,
                dest = Slot(
                    name = None,
                    index = i,
                    register_set = Register_set.ARGUMENTS,
                ),
            ))

            param_t = type_signature['parameters'][i]
            arg_t = st.type_of(slot)
            viuact.util.log.raw('call to {}: [{}] p{{ {} }} -> a{{ {} }}'.format(
                called_fn_name,
                i,
                param_t,
                arg_t,
            ))

            m, template_parameters = param_t.match(arg_t, template_parameters)
            if not m:
                raise viuact.errors.Bad_argument_type(
                    arg.first_token().at(),
                    called_fn_name,
                    i,
                    param_t,
                    arg_t,
                )

            # FIXME Maybe mark the slot as moved in some way to aid with error
            # reporting?
            sc.deallocate_slot(slot)

    return_t = type_signature['return']
    if return_t.polymorphic():
        return_t = template_parameters[return_t.name()]
    st.type_of(result, return_t)

    body.append(Call(
        to = called_fn_name,
        slot = result,
        kind = Call.Kind.Synchronous,
    ))
    body.append(Verbatim(''))

    return result

def emit_primitive_literal(mod, body, st, result, expr):
    lit = expr.value()
    if type(lit) == viuact.lexemes.String:
        body.append(Ctor(
            of_type = 'string',
            slot = result,
            value = str(lit),
        ))
        st.type_of(result, Type.string())
        return result
    if type(lit) == viuact.lexemes.Integer:
        body.append(Ctor(
            of_type = 'integer',
            slot = result,
            value = str(lit),
        ))
        st.type_of(result, Type.i8())
        return result
    viuact.util.log.fixme('failed to emit primitive literal: {}'.format(
        typeof(lit)))
    raise None

def emit_let_binding(mod, body, st, binding):
    name = binding.name()
    body.append(Verbatim('; let {} = ...'.format(str(name))))
    slot = st.get_slot(
        name = str(name),
        register_set = Register_set.LOCAL,
    )
    with st.scoped() as sc:
        slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            # Don't use an additional scope here as let-bindings should introduce
            # new variables into the current scope.
            result = slot,
            expr = binding.val(),
        )
    body.append(Verbatim(''))
    return slot

def emit_compound_expr(mod, body, st, result, expr):
    for i, each in enumerate(expr.body()):
        last = (i == (len(expr.body()) - 1))
        slot = None
        if type(each) is viuact.forms.Let_binding:
            slot = emit_let_binding(
                mod = mod,
                body = body,
                st = st,
                binding = each,
            )
        else:
            with st.scoped() as sc:
                slot = emit_expr(
                    mod = mod,
                    body = body,
                    st = sc,
                    result = (result if last else Slot.make_void()),
                    expr = each,
                )
        if last:
            result = slot

    return result

def emit_if(mod, body, st, result, expr):
    guard_slot = st.get_slot(name = None)
    viuact.util.log.raw('if: guard_slot = {}'.format(guard_slot.to_string()))

    with st.scoped() as sc:
        emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = guard_slot,
            expr = expr.guard(),
        )

    label_core = hashlib.sha1('{}+{}+{}'.format(
        mod.name(),
        st.fn(),
        st.special(),
    ).encode('utf-8')).hexdigest()
    label_true = 'if_true_' + label_core
    label_false = 'if_false_' + label_core
    label_end = 'if_end_' + label_core

    body.append(Verbatim('if {} {} {}'.format(
        guard_slot.to_string(),
        label_true,
        label_false,
    )))
    st.deallocate_slot(guard_slot)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_true)))
    with st.scoped() as sc:
        emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = result,
            expr = expr.arm_true(),
        )
        body.append(Verbatim('jump {}'.format(label_end)))

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_false)))
    with st.scoped() as sc:
        emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = result,
            expr = expr.arm_false(),
        )

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_end)))

    # viuact.util.log.raw('---- 8< ----')
    st.actual_pressure(Register_set.LOCAL)
    # viuact.util.log.raw('---- >8 ----')

    return result

def emit_expr(mod, body, st, result, expr):
    if type(expr) is viuact.forms.Fn_call:
        return emit_fn_call(
            mod = mod,
            body = body,
            st = st,
            result = result,
            form = expr,
        )
    if type(expr) is viuact.forms.Compound_expr:
        return emit_compound_expr(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Primitive_literal:
        return emit_primitive_literal(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Name_ref:
        if not result.is_void():
            # viuact.util.log.warning(
            #     'slot will be unused after name-ref emission: {} = {}'.format(
            #         result.to_string(),
            #         str(expr.name()),
            #     ))
            st.cancel_slot(result)
        return st.slot_of(str(expr.name()))
    if type(expr) is viuact.forms.Let_binding:
        if not result.is_void():
            viuact.util.log.warning(
                'slot will be unused after let-binding emission: {} = {}'.format(
                    result.to_string(),
                    str(expr.name()),
                ))
        return emit_let_binding(
            mod = mod,
            body = body,
            st = st,
            binding = expr,
        )
    if type(expr) is viuact.forms.If:
        return emit_if(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    viuact.util.log.fixme('failed to emit expression: {}'.format(
        typeof(expr)))
    raise None

def cc_fn(mod, fn):
    viuact.util.log.print('cc.fn: {}::{}/{}'.format(
        mod.name(),
        fn.name(),
        len(fn.parameters()),
    ))

    fn_name = '{}/{}'.format(fn.name(), len(fn.parameters()))
    main_fn_name = (
        '{}::{}/{}'.format(mod.name(), fn_name)
        if mod.name() != EXEC_MODULE else
        fn_name)
    signature = mod.signature(fn_name)

    st = State(fn = main_fn_name)
    main_fn = Fn_cc(main_fn_name)
    out = CC_out(main_fn)

    for i, each in enumerate(fn.parameters()):
        source = Slot.make_anonymous(i, Register_set.PARAMETERS)
        label = (
            str(each)[1:]
            if type(each) is viuact.forms.Labelled_parameter else
            str(each)
        )
        dest = st.get_slot(label)
        st.type_of(dest, signature['parameters'][i])
        main_fn.append(Move.make_move(
            source = source,
            dest = dest,
        ))

    result_slot = Slot(None, 0, Register_set.LOCAL)
    st.insert_allocated(result_slot)
    result = emit_expr(
        mod = mod,
        body = main_fn,
        st = st,
        result = result_slot,
        expr = fn.body(),
    )

    if signature['return'] != st.type_of(result):
        raise viuact.errors.Bad_returned_type(
            (0, 0,),  # FIXME add position
            # signature['return'],
            fn_name,
            signature['return'],
            st.type_of(result),
        )
        raise 0

    main_fn.body.insert(0, Verbatim(''))
    main_fn.body.insert(0, Verbatim('allocate_registers %{} local'.format(
        # st.static_pressure(),
        st.actual_pressure(Register_set.LOCAL),
    )))
    main_fn.append(Verbatim('return'))

    return out

def cc_type(mod, form):
    # FIXME Add checks if used types were defined before.
    # FIXME Add checks for used template parameters - if they are defined by the
    # val expression.
    t = Type.t(
        name = str(form.name()),
        parameters = tuple([cc_type(mod, each) for each in form.parameters()]),
    )
    viuact.util.log.raw('cc.type: {}'.format(t))
    return t


def cc(source_root, source_file, module_name, forms, output_directory):
    output_file = os.path.normpath(os.path.splitext(source_file)[0] + '.asm')

    viuact.util.log.print('cc: [{}]/{} -> {}/{}'.format(
        source_root,
        source_file[len(source_root) + 1:],
        output_directory,
        output_file,
    ))

    mod = Module_info(module_name, source_file)

    for each in filter(lambda x: type(x) is viuact.forms.Val_fn_spec, forms):
        mod.make_fn_signature(
            name = each.name(),
            parameters = [cc_type(mod, t) for t in each.parameter_types()],
            return_type = cc_type(mod, each.return_type()),
            template_parameters = [
                cc_type(mod, t) for t in each.template_parameters()],
        )

    for each in forms:
        if type(each) is not viuact.forms.Fn:
            continue
        mod.make_fn(
            name = each.name(),
            parameters = each.parameters(),
        )

    function_bodies = {}

    print(';')
    if mod.name() == EXEC_MODULE:
        print('; Function definitions')
    else:
        print('; Function definitions for module {}'.format(mod.name()))
    print(';')

    for each in filter(lambda x: type(x) is viuact.forms.Fn, forms):
        out = cc_fn(mod, each)
        print()
        print('.function: {}'.format(out.main.name))
        for line in out.main.body:
            print('    {}'.format(line.to_string()))
        print('.end')
