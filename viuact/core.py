import enum
import os

import viuact.util.log
import viuact.forms


EXEC_MODULE = '<main>'

BUILTIN_FUNCTIONS = (
    'print',
)


def typeof(value):
    return str(type(value))[8:-2]


class Module_info:
    def __init__(self, name, source_file):
        self._name = name
        self._source_file = source_file

        self._functions = {}

    def name(self):
        return self._name

    def make_fn(self, name, parameters):
        n = '{}/{}'.format(name, len(parameters))
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

class State:
    def __init__(self, upper = None, parent = None):
        self._upper = upper     # Used for closures.
        self._parent = parent   # Parent scope, e.g. for function call
                                # arguments.
        self._next_slot_index = {
            Register_set.LOCAL: 1,
        }
        self._named_slots = {}
        self._allocated_slots = []
        self._freed_slots = []

        if parent is not None:
            for k, v in self._parent._next_slot_index.items():
                self._next_slot_index[k] = v

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
        self._parent._freed_slots.extend(self._freed_slots)
        self._parent.push_deallocations()
        self._freed_slots.clear()

    def deallocate_slot(self, slot):
        self._allocated_slots.remove((slot.index, slot.register_set,))
        self._freed_slots.append(slot)
        # viuact.util.log.note('  freed slot: {}'.format(slot.to_string()))
        return self

    def find_free_slot(self, register_set):
        for each in self._freed_slots:
            if each.register_set == register_set:
                viuact.util.log.note('reusing slot {}'.format(each.to_string()))
                self._freed_slots.remove(each)
                return each
        if self._parent is not None:
            return self._parent.find_free_slot(register_set)
        return None

    def allocate_slot(self, register_set):
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
        return self._next_slot_index[register_set]

    def scoped(self):
        s = State(parent = self)
        # viuact.util.log.note('created scope: {}'.format(s))
        return Scope(s)

    def erase(self):
        # viuact.util.log.note('erasing scope {} with {} slot(s)...'.format(
        #     self, len(self._allocated_slots)))
        for each in self._allocated_slots:
            i, r = each
            self.deallocate_slot(Slot(
                name = None,
                index = i,
                register_set = r,
            ))
        self.push_deallocations()


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
                result = result,
                expr = form.arguments()[0],
            )
            body.append(Verbatim('print {}'.format(
                slot.to_string(),
            )))

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

    body.append(Verbatim('frame %{} arguments'.format(len(form.arguments()))))

    for i, arg in enumerate(form.arguments()):
        body.append(Verbatim('; for argument {}'.format(i)))
        with st.scoped() as sc:
            slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = st.get_slot(name = None),
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
        return result
    if type(lit) == viuact.lexemes.Integer:
        body.append(Ctor(
            of_type = 'integer',
            slot = result,
            value = str(lit),
        ))
        return result
    viuact.util.log.fixme('failed to emit primitive literal: {}'.format(
        typeof(lit)))
    raise None

def emit_let_binding(mod, body, st, binding):
    name = binding.name()
    body.append(Verbatim('; let {} = ...'.format(str(name))))
    with st.scoped() as sc:
        slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            # Don't use an additional scope here as let-bindings should introduce
            # new variables into the current scope.
            result = st.get_slot(
                name = str(name),
                register_set = Register_set.LOCAL,
            ),
            expr = binding.val(),
        )
    body.append(Verbatim(''))
    return slot

def emit_compound_expr(mod, body, st, result, expr):
    for i, each in enumerate(expr.body()):
        last = (i == (len(expr.body()) - 1))
        if type(each) is viuact.forms.Let_binding:
            emit_let_binding(
                mod = mod,
                body = body,
                st = st,
                binding = each,
            )
        else:
            with st.scoped() as sc:
                emit_expr(
                    mod = mod,
                    body = body,
                    st = sc,
                    result = (result if last else Slot.make_void()),
                    expr = each,
                )

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
            viuact.util.log.warning(
                'slot will be unused after name-ref emission: {} = {}'.format(
                    result.to_string(),
                    str(expr.name()),
                ))
        return st.slot_of(str(expr.name()))
    if type(expr) is viuact.forms.Let_binding:
        if not result.is_void():
            viuact.util.log.warning(
                'slot will be unused after name-ref emission: {} = {}'.format(
                    result.to_string(),
                    str(expr.name()),
                ))
        return emit_let_binding(
            mod = mod,
            body = body,
            st = st,
            binding = expr,
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

    main_fn_name = (
        '{}::{}/{}'.format(mod.name(), fn.name(), len(fn.parameters()))
        if mod.name() != EXEC_MODULE else
        '{}/{}'.format(fn.name(), len(fn.parameters())))

    st = State()
    main_fn = Fn_cc(main_fn_name)
    out = CC_out(main_fn)

    for i, each in enumerate(fn.parameters()):
        source = Slot.make_anonymous(i, Register_set.PARAMETERS)
        label = (
            str(each)[1:]
            if type(each) is viuact.lexemes.Labelled_name else
            str(each)
        )
        dest = st.get_slot(label)
        main_fn.append(Move.make_move(
            source = source,
            dest = dest,
        ))

    result = emit_expr(
        mod = mod,
        body = main_fn,
        st = st,
        result = Slot(None, 0, Register_set.LOCAL),
        expr = fn.body(),
    )

    main_fn.body.insert(0, Verbatim(''))
    main_fn.body.insert(0, Verbatim('allocate_registers %{} local'.format(
        # st.static_pressure(),
        st.actual_pressure(Register_set.LOCAL),
    )))
    main_fn.append(Verbatim('return'))

    return out


def cc(source_root, source_file, module_name, forms, output_directory):
    output_file = os.path.normpath(os.path.splitext(source_file)[0] + '.asm')

    viuact.util.log.print('cc: [{}]/{} -> {}/{}'.format(
        source_root,
        source_file[len(source_root) + 1:],
        output_directory,
        output_file,
    ))

    mod = Module_info(module_name, source_file)

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
