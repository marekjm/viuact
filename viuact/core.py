import enum
import hashlib
import os

import viuact.util.log
import viuact.forms
import viuact.typesystem.t
import viuact.typesystem.state

from viuact.util.type_annotations import T, I, Alt


EXEC_MODULE = '<main>'

BUILTIN_FUNCTIONS = (
    'print',
)


def typeof(value):
    return str(type(value))[8:-2]


class Type:
    class Int(viuact.typesystem.t.Value):
        SIGNED_INTEGER_TYPES = (
            'i8',
            'i16',
            'i32',
            'i64',
        )
        UNSIGNED_INTEGER_TYPES = (
            'u8',
            'u16',
            'u32',
            'u64',
        )
        INTEGER_TYPES = (SIGNED_INTEGER_TYPES + UNSIGNED_INTEGER_TYPES)

        def cast_from(self, t):
            if t.to_string() not in Type.Int.INTEGER_TYPES:
                return False

            # Integers should be classified according to:
            #
            #   - signedness: signed and unsigned
            #   - bit width: 1, 4, 8, 16, 32, 64
            #   - endiannes: host, little, and big
            #   - overflow behaviour: wraparound, trap, saturate
            #
            # For example, a UNIX socket port could be represented using an
            # unsigned, 16-bit, big-endian, trapping integer.
            #
            # A PID counter could be represented using an unsigned, 64-bit,
            # host-endian, wraparound integer.
            this_t = self.to_string()
            that_t = t.to_string()
            same_subtype = lambda prefix: (this_t.startswith(prefix) ==
                    that_t.startswith(prefix))
            if not same_subtype('i'):
                return False

            bitwidth_this = int(self.to_string()[1:])
            bitwidth_that = int(self.to_string()[1:])
            return (bitwidth_this >= bitwidth_that)

        @staticmethod
        def is_integer_type(t):
            tt = (I(viuact.typesystem.t.Value) | t)
            return (tt.to_string() in Type.Int.INTEGER_TYPES)

    def string():
        return viuact.typesystem.t.Value(
            name = 'string',
        )

    def i8():
        return Type.Int(
            name = 'i8',
        )

    def i16():
        return Type.Int(
            name = 'i16',
        )

    def i32():
        return Type.Int(
            name = 'i32',
        )

    def i64():
        return Type.Int(
            name = 'i64',
        )

    def u8():
        return Type.Int(
            name = 'u8',
        )

    def u16():
        return Type.Int(
            name = 'u16',
        )

    def u32():
        return Type.Int(
            name = 'u32',
        )

    def u64():
        return Type.Int(
            name = 'u64',
        )

    def bool():
        return viuact.typesystem.t.Value(
            name = 'bool',
        )

    def atom():
        return viuact.typesystem.t.Value(
            name = 'atom',
        )


class Module_info:
    def __init__(self, name, source_file):
        self._name = name
        self._source_file = source_file

        self._functions = {}
        self._function_signatures = {}

        self._enums = {}
        self._records = {}
        self._exceptions = {}

    def name(self):
        return self._name

    def make_fn(self, name, parameters):
        n = '{}/{}'.format(name, len(parameters))
        if n not in self._function_signatures:
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
        # viuact.util.log.print('module info [{}]: visible local fn {}'.format(
        #     self._name,
        #     n,
        # ))
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

    def make_enum(self, name, fields, template_parameters):
        if len(template_parameters) > 1:
            raise viuact.errors.Fail(
                name.tok().at(),
                'FIXME enums support at most one type parameter',
            )
        self._enums[str(name)] = {
            'fields': {
                str(f.name()) : {
                    'index': i,
                    'field': f,
                }
                for i, f
                in enumerate(fields)
            },
            'template_parameters': template_parameters,
        }
        return self

    def enum(self, name):
        # FIXME error checking
        return self._enums[str(name)]

    def enums(self):
        return list(self._enums.keys())

    def make_record(self, name, fields):
        self._records[str(name)] = {
            'fields': {
                str(f.name()) : f.type()
                for f
                in fields
            },
        }

    def record(self, name):
        return self._records[str(name)]

    def records(self):
        return list(self._records.keys())

    def make_exception(self, tag, value):
        self._exceptions[str(tag)] = value
        return self

    def exception(self, name):
        # FIXME error checking
        return self._exceptions[str(name)]


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

        # Disposable slot is allocated automatically by the compiler for its own
        # needs (eg. to store a temporary value). Such a slot may be freely
        # cancelled or freed, as it is not accessible to the program being
        # compiled (eg. it is dropped immediately after use).
        #
        # The compiler may automatically drop such a slot and replace it with a
        # non-disposable one it if detects that it is required.
        self._is_disposable = False

        # Viuact by default dereferences pointers. This has several interesting
        # results: the printing is pretty by default, and pointers work like
        # references.
        #
        # However, sometimes you do not want the dereference to take place, you
        # want the real deal - the bare, naked, raw pointer. If that is the case
        # then you have to use the ampersand operator in the expression that
        # would be dereferenced to inhibit the default behaviour. The result
        # slot will then be given to the expression's emitter with a note that
        # the automatic dereference should not be performed.
        #
        # By the way, this is also how you create pointers in Viuact - by
        # inhibiting the automatic dereference. Compare this code, which moves
        # the value between variables:
        #
        #       (let a    42)
        #       (let a'   a)
        #
        # with this code, where a' is a pointer to a:
        #
        #       (let a    42)
        #       (let a'   (& a))
        #
        self._inhibit_dereference = False

    def __eq__(self, other):
        if type(other) is not Slot:
            raise TypeError('cannot compare Slot to {}: {}'.format(
                other.__class__.__name__,
                other,
            ))
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

    def make_copy(self):
        s = Slot(
            name = self.name,
            index = self.index,
            register_set = self.register_set,
        )
        s._is_pointer = self.is_pointer()
        s._is_disposable = self.is_disposable()
        s._inhibit_dereference = self.inhibit_dereference()
        return s

    def is_void(self):
        return (self.register_set == Register_set.VOID)

    def is_anonymous(self):
        return (self.name is None)

    def is_pointer(self):
        return self._is_pointer

    def as_pointer(self, pointer = True):
        s = self.make_copy()
        s._is_pointer = pointer
        return s

    def inhibit_dereference(self, inhibit = None):
        if inhibit is None:
            return self._inhibit_dereference

        s = self.make_copy()
        s._inhibit_dereference = T(bool) | inhibit
        return s

    def is_disposable(self):
        return self._is_disposable

    def as_disposable(self, disposable = True):
        s = self.make_copy()
        s._is_disposable = disposable
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

    def exit(self, *args):
        self.__exit__(*args)

class State:
    def __init__(self, fn, upper = None, parent = None, special = 0, types =
            None):
        self._fn = fn           # Name of the function for which this state was
                                # created.
        self._special = special # General purpose counter for special events.

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
        self._permanent_slots = set()

        self._types = (viuact.typesystem.state.State() if types is None else types)

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

        try:
            if slot in self._freed_slots:
                raise viuact.errors.Double_deallocation(slot)
            if slot in self._cancelled_slots:
                raise viuact.errors.Deallocation_of_cancelled(slot)
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
        return self

    def deallocate_slot_if_anonymous(self, slot):
        if slot.is_anonymous():
            self.deallocate_slot(slot)
        return self

    def mark_permanent(self, slot):
        self.assert_active()
        self._permanent_slots.add(slot.to_string())

    def is_permanent(self, slot):
        return (slot.to_string() in self._permanent_slots)

    def cancel_slot(self, slot):
        self.assert_active()
        if slot.is_void():
            return self

        try:
            if slot in self._cancelled_slots:
                raise viuact.errors.Double_cancel(slot)
            if slot in self._freed_slots:
                raise viuact.errors.Cancel_of_deallocated(slot)
            if self.is_permanent(slot):
                return self
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
                self._cancelled_slots.remove(each)
                return each
        for each in self._freed_slots:
            if each.register_set == register_set:
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

    def all_allocated_slots(self):
        slots = self._allocated_slots[:]
        if self._parent is not None:
            slots.extend(self._parent.all_allocated_slots())
        return slots
    def all_freed_slots(self):
        slots = self._freed_slots[:]
        if self._parent is not None:
            slots.extend(self._parent.all_freed_slots())
        return slots
    def all_cancelled_slots(self):
        slots = self._cancelled_slots[:]
        if self._parent is not None:
            slots.extend(self._parent.all_cancelled_slots())
        return slots

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
            self._named_slots[name] = slot

        return slot

    def get_anonymous_slot(self, register_set = Register_set.DEFAULT):
        self.assert_active()

        slot = Slot(
            None,
            self.allocate_slot(register_set),
            register_set,
        )

        return slot

    def get_disposable_slot(self, register_set = Register_set.DEFAULT):
        self.assert_active()

        slot = Slot(
            None,
            self.allocate_slot(register_set),
            register_set,
        )

        return slot.as_disposable()

    def slot_of(self, name):
        try:
            return self._named_slots[name]
        except KeyError:
            if self._parent is None:
                raise
            return self._parent.slot_of(name)

    def name_slot(self, slot, name):
        x = (slot.index, slot.register_set,)
        if x not in self._allocated_slots:
            if self._parent:
                return self._parent.name_slot(slot, name)
            raise KeyError(slot.to_string())
        self._named_slots[name] = slot
        return self

    def actual_pressure(self, register_set):
        n = self._next_slot_index[register_set]
        a = self._allocated_slots
        f = list(filter(
            lambda i: i.register_set == register_set, self._freed_slots))

        a = (max(list(map(lambda x: x[0], a))) if a else None)
        f = (max(list(map(lambda x: x.index, f))) if f else None)

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

        return max(pressure, n)

    def scoped(self):
        self._active = False
        s = State(
            fn = self.fn(),
            parent = self,
            special = self._special,
            types = self._types,
        )
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
        self._parent._special = self._special

    def fn(self):
        return self._fn

    def special(self):
        n = self._special
        self._special += 1
        return n

    def _set_type_of(self, slot, t):
        if type(slot) is not Slot:
            raise TypeError('cannot set type of non-slot {}: {}'.format(
                typeof(slot),
                slot,
            ))
        if slot.is_void():
            raise TypeError('cannot set type of void slot')
        key = slot.to_string()
        if (slot.index, slot.register_set,) not in self._allocated_slots:
            raise KeyError(slot.to_string())
        return self._types.store(key, t)

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
            raise viuact.errors.Read_of_untyped_slot(slot)
        t = self._types.load(key)
        return t

    def type_of(self, slot, t = None):
        try:
            if t is None:
                return self._get_type_of(slot)
            else:
                return self._set_type_of(slot, t)
        except (KeyError, viuact.errors.Read_of_untyped_slot,):
            if self._parent:
                return self._parent.type_of(slot, t)
            else:
                raise

    def remove_type(self, slot):
        self.assert_active()
        if type(slot) is str:
            self._types.erase(slot)
        elif type(slot) is Slot:
            if slot.is_void():
                raise None
            key = None
            if slot.is_anonymous():
                key = slot.to_string()
            else:
                key = slot.name
            try:
                self._types.erase(key)
            except KeyError:
                # The slot has no type assigned.
                pass
        else:
            raise None

    def unify_types(self, a, b):
        return viuact.typesystem.state.unify(
            state = self._types,
            left = a,
            right = b,
        )

    def store(self, key, t):
        return self._types.store(key, t)

    def register_template_variable(self, p):
        return self._types.register_type(p)


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

class Comment:
    def __init__(self, text):
        self.text = text

    def to_string(self):
        return '; {}'.format(self.text)

class Print:
    PRINT = 'print'
    ECHO = 'echo'

    def __init__(self, slot : Slot, kind : str):
        self.slot = T(Slot) | slot
        self.kind = kind

    def __repr__(self):
        return '{}: {}'.format(self.kind, repr(self.text))

    def to_string(self):
        return '{} {}'.format(self.kind, self.slot.to_string())

class Ctor:
    TAG_ENUM_TAG_FIELD = repr('tag')
    TAG_ENUM_VALUE_FIELD = repr('value')

    def __init__(self, of_type : str, slot : Slot, value : str):
        self.of_type = of_type
        self.slot = T(Slot) | slot
        self.value = value

    def to_string(self):
        return '{} {} {}'.format(
            self.of_type,
            self.slot.to_string(),
            self.value,
        )

class Cmp:
    EQ = 'eq'

    def __init__(self, kind : str, slot : Slot, rhs : Slot, lhs : Slot):
        self.kind = kind
        self.slot = T(Slot) | slot
        self.rhs = T(Slot) | rhs
        self.lhs = T(Slot) | lhs

    def to_string(self):
        return '{} {} {} {}'.format(
            self.kind,
            self.slot.to_string(),
            self.rhs.to_string(),
            self.lhs.to_string(),
        )

class If:
    def __init__(self, cond : Slot, if_true : str, if_false : str):
        self.condition = T(Slot) | cond
        self.if_true = if_true
        self.if_false = if_false

    def to_string(self):
        return 'if {} {} {}'.format(
            self.condition.to_string(),
            self.if_true,
            self.if_false,
        )

class Jump:
    def __init__(self, label : str):
        self.label = label

    def to_string(self):
        return 'jump {}'.format(
            self.label,
        )

class Return:
    def __init__(self):
        pass

    def to_string(self):
        return 'return'

class Marker:
    def __init__(self, label : str):
        self.label = label

    def to_string(self):
        return '.mark: {}'.format(
            self.label,
        )

class Move:
    MOVE = 'move'
    COPY = 'copy'
    DELETE = 'delete'
    POINTER = 'ptr'

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

    @staticmethod
    def make_pointer(source, dest):
        return Move(
            Move.POINTER,
            source,
            dest,
        )

    def __init__(self, of_type : str, source : Slot, dest : Slot):
        self.of_type = of_type

        if source.is_void():
            raise viuact.errors.Source_cannot_be_void(
                (0, 0), '{} to {}'.format(of_type, dest.to_string()))

        self.source = T(Slot) | source
        self.dest = T(Slot) | dest

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
        self.slot = T(Slot) | slot
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
                result = (
                    sc.get_disposable_slot().inhibit_dereference(result.inhibit_dereference())
                    if result.is_void()
                    else result
                ),
                expr = form.arguments()[0],
            )
            arg_t = sc.type_of(slot)
            if arg_t == viuact.typesystem.t.Void():
                raise viuact.errors.Read_of_void(
                    pos = form.arguments()[0].first_token().at(),
                    by = 'print function',
                )

            # st.store(slot.to_string(), Type.void())

            is_pointer = (type(arg_t) is viuact.typesystem.t.Pointer)
            dereference_freely = (not slot.inhibit_dereference())
            deref = (is_pointer and dereference_freely)
            body.append(Print(slot.as_pointer(deref), Print.PRINT))
            body.append(Verbatim(''))

        return slot

def emit_indirect_fn_call(mod, body, st, result, form):
    name = str(form.to().name())
    fn_slot = st.slot_of(name)
    fn_t = st.type_of(fn_slot)

    if len(fn_t.parameter_types()) != len(form.arguments()):
        e = viuact.errors.Invalid_arity(
            form.to().name().tok().at(),
            'from variable {}'.format(name),
        ).note('expected {} argument(s), got {}'.format(
            len(fn_t.parameters()),
            len(form.arguments()),
        ))
        raise e

    body.append(Verbatim('frame %{} arguments'.format(len(form.arguments()))))

    parameter_types = fn_t.parameter_types()
    args = form.arguments()
    for i, arg in enumerate(args):
        body.append(Verbatim('; for argument {}'.format(i)))
        arg_slot = st.get_slot(name = None)
        with st.scoped() as sc:
            slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = arg_slot,
                expr = arg,
            )
            body.append(Move.make_move(
                source = arg_slot,
                dest = Slot(
                    name = None,
                    index = i,
                    register_set = Register_set.ARGUMENTS,
                ),
            ))

            param_t = parameter_types[i]
            arg_t = st.type_of(arg_slot)

            try:
                st.unify_types(param_t, arg_t)
            except viuact.typesystem.state.Cannot_unify:
                raise viuact.errors.Bad_argument_type(
                    arg.first_token().at(),
                    name,
                    (i + 1),
                    st._types.stringify_type(param_t, human_readable = True),
                    st._types.stringify_type(arg_t, human_readable = True),
                )

            # FIXME Maybe mark the slot as moved in some way to aid with error
            # reporting?
            sc.deallocate_slot(arg_slot)

    return_t = fn_t.return_type()

    # Only set type of the result is not a void register (it does not make sense
    # to assign type to a void).
    if not result.is_void():
        st.type_of(result, return_t)

    body.append(Call(
        to = fn_slot.to_string(),
        slot = result,
        kind = Call.Kind.Synchronous,
    ))
    body.append(Verbatim(''))

    return result

def emit_direct_fn_call(mod, body, st, result, form):
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

    type_signature = mod.signature(called_fn_name)

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

    parameter_types = []
    tmp = {}
    for each in type_signature['template_parameters']:
        tmp[viuact.typesystem.t.Template(each.name()[1:])] = st.register_template_variable(each)
    for each in type_signature['parameters']:
        if type(each) is viuact.typesystem.t.Value:
            parameter_types.append(each.concretise(tmp))
        elif type(each) is viuact.typesystem.t.Fn:
            parameter_types.append(each.concretise(tmp))
        else:
            raise None

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

            param_t = parameter_types[i]
            arg_t = st.type_of(slot)

            try:
                st.unify_types(param_t, arg_t)
            except viuact.typesystem.state.Cannot_unify:
                raise viuact.errors.Bad_argument_type(
                    arg.first_token().at(),
                    called_fn_name,
                    (i + 1),
                    st._types.stringify_type(param_t, human_readable = True),
                    st._types.stringify_type(arg_t, human_readable = True),
                )

            # FIXME Maybe mark the slot as moved in some way to aid with error
            # reporting?
            sc.deallocate_slot(slot)

    return_t = type_signature['return'].concretise(tmp)

    # Only set type of the result is not a void register (it does not make sense
    # to assign type to a void).
    if not result.is_void():
        st.type_of(result, return_t)

    body.append(Call(
        to = called_fn_name,
        slot = result,
        kind = Call.Kind.Synchronous,
    ))
    body.append(Verbatim(''))

    return result

def emit_fn_call(mod, body, st, result, form):
    if str(form.to().name()) in BUILTIN_FUNCTIONS:
        return emit_builtin_call(mod, body, st, result, form)

    base_name = str(form.to().name().tok())
    try:
        # Let's see if the base name is a name of a slot. If that is the case
        # this is an indirect call and we have to employ slightly different
        # machinery to emit it, than what would be used for direct calls.
        st.slot_of(base_name)
        return emit_indirect_fn_call(mod, body, st, result, form)
    except KeyError:
        pass

    return emit_direct_fn_call(mod, body, st, result, form)

def emit_operator_concat(mod, body, st, result, expr):
    if len(expr.arguments()) < 2:
        raise viuact.errors.Invalid_arity(
            pos = expr.operator().tok().at(),
            s = str(expr.operator()),
            kind = viuact.errors.Invalid_arity.OPERATOR,
        ).note('expected at least 2 arguments, got {}'.format(
            len(expr.arguments()),
        ))

    with st.scoped() as sc:
        lhs_slot = sc.get_slot(None)
        rhs_slot = sc.get_slot(None)

        args = expr.arguments()

        lhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = lhs_slot,
            expr = args[0],
        )
        rhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = rhs_slot,
            expr = args[1],
        )
        arg_t = sc.type_of(rhs_slot)
        if arg_t.to_string() != Type.string().to_string():
            is_pointer = (type(arg_t) is viuact.typesystem.t.Pointer)
            dereference_freely = (not rhs_slot.inhibit_dereference())
            deref = (is_pointer and dereference_freely)
            body.append(Verbatim('text {} {}'.format(
                rhs_slot.to_string(),
                rhs_slot.as_pointer(deref).to_string(),
            )))
        body.append(Verbatim('textconcat {} {} {}'.format(
            result.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))

        for each in args[2:]:
            rhs_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = rhs_slot,
                expr = each,
            )
            arg_t = sc.type_of(rhs_slot)
            if arg_t.to_string() != Type.string().to_string():
                is_pointer = (type(arg_t) is viuact.typesystem.t.Pointer)
                dereference_freely = (not rhs_slot.inhibit_dereference())
                deref = (is_pointer and dereference_freely)
                body.append(Verbatim('text {} {}'.format(
                    rhs_slot.to_string(),
                    rhs_slot.as_pointer(deref).to_string(),
                )))
            body.append(Verbatim('textconcat {} {} {}'.format(
                result.to_string(),
                result.to_string(),
                rhs_slot.to_string(),
            )))

        st.type_of(result, Type.string())

    return result

def emit_arithmetic_operator(mod, body, st, result, expr):
    if len(expr.arguments()) < 2:
        raise viuact.errors.Invalid_arity(
            pos = expr.operator().tok().at(),
            s = str(expr.operator()),
            kind = viuact.errors.Invalid_arity.OPERATOR,
        ).note('expected at least 2 arguments, got {}'.format(
            len(expr.arguments()),
        ))

    operator_ops = {
        '+': 'add',
        '-': 'sub',
        '*': 'mul',
        '/': 'div',
    }
    op = operator_ops[str(expr.operator().tok())]

    with st.scoped() as sc:
        lhs_slot = sc.get_slot(None)
        rhs_slot = sc.get_slot(None)

        args = expr.arguments()

        lhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = lhs_slot,
            expr = args[0],
        )
        rhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = rhs_slot,
            expr = args[1],
        )
        body.append(Verbatim('{} {} {} {}'.format(
            op,
            result.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))

        ret_t = sc.type_of(lhs_slot)
        if not Type.Int.is_integer_type(ret_t):
            raise viuact.errors.Type_mismatch(
                pos = args[0].first_token().at(),
                a = '<any integer type>',
                b = ret_t.to_string(),
            ).note('arithmetic operator {} requires integer operands'.format(
                str(expr.operator().tok()),
            ))

        sc.unify_types(ret_t, sc.type_of(rhs_slot))

        for each in args[2:]:
            rhs_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = rhs_slot,
                expr = each,
            )
            sc.unify_types(ret_t, sc.type_of(rhs_slot))
            body.append(Verbatim('{} {} {} {}'.format(
                op,
                result.to_string(),
                result.to_string(),
                rhs_slot.to_string(),
            )))

        sc.deallocate_slot(lhs_slot)
        sc.deallocate_slot(rhs_slot)

        st.type_of(result, ret_t)

    return result

def emit_comparison_operator(mod, body, st, result, expr):
    if len(expr.arguments()) != 2:
        raise viuact.errors.Invalid_arity(
            pos = expr.operator().tok().at(),
            s = str(expr.operator()),
            kind = viuact.errors.Invalid_arity.OPERATOR,
        ).note('expected 2 arguments, got {}'.format(
            len(expr.arguments()),
        ))

    operator_ops = {
        '>':  'gt',
        '>=': 'gte',
        '<':  'lt',
        '<=': 'lte',
        '=':  'eq',
        '!=': 'eq',
    }
    op = operator_ops[str(expr.operator().tok())]

    with st.scoped() as sc:
        lhs_slot = sc.get_slot(None)
        rhs_slot = sc.get_slot(None)

        args = expr.arguments()

        lhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = lhs_slot,
            expr = args[0],
        )
        rhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = rhs_slot,
            expr = args[1],
        )
        body.append(Verbatim('{} {} {} {}'.format(
            op,
            result.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))
        if str(expr.operator().tok()) == '!=':
            body.append(Verbatim('not {}'.format(result.to_string())))

        sc.deallocate_slot(lhs_slot)
        sc.deallocate_slot(rhs_slot)

        st.type_of(result, Type.bool())

    return result

def emit_operator_call(mod, body, st, result, expr):
    ARITHMETIC_OPERATORS = (
        viuact.lexemes.Operator_plus,
        viuact.lexemes.Operator_minus,
        viuact.lexemes.Operator_star,
        viuact.lexemes.Operator_solidus,
    )
    CMP_OPERATORS = (
        viuact.lexemes.Operator_lte,
        viuact.lexemes.Operator_lt,
        viuact.lexemes.Operator_gte,
        viuact.lexemes.Operator_gt,
        viuact.lexemes.Operator_neq,
        viuact.lexemes.Operator_eq,
    )
    if type(expr.operator()) is viuact.lexemes.Operator_concat:
        return emit_operator_concat(mod, body, st, result, expr)
    elif type(expr.operator()) in ARITHMETIC_OPERATORS:
        return emit_arithmetic_operator(mod, body, st, result, expr)
    elif type(expr.operator()) in CMP_OPERATORS:
        return emit_comparison_operator(mod, body, st, result, expr)
    raise None

def emit_enum_ctor_call(mod, body, st, result, form):
    from_module = form.to().module()
    enum_name = form.to().of_enum()
    enum_field = form.to().field()

    enum = (
        mod.module(from_module).enum(enum_name)
        if from_module else
        mod.enum(enum_name)
    )

    field = enum['fields'][str(enum_field)]

    # FIXME embed typing requirement into the list...
    ts = []
    for each in enum['template_parameters']:
        # FIXME ...instead of checking it here
        ts.append(Alt(
            I(viuact.typesystem.t.Base),
            T(viuact.typesystem.t.Template),
        ) | st.register_template_variable(each))

    body.append(Verbatim('struct {}'.format(result.to_string())))
    enum_t = st.type_of(result, viuact.typesystem.t.Value(
        name = str(enum_name),
        templates = tuple(ts),
    ))

    with st.scoped() as sc:
        key = sc.get_slot(name = None)
        body.append(Ctor(
            of_type = 'atom',
            slot = key,
            value = repr('key'),
        ))

        value = sc.get_slot(name = None)
        body.append(Ctor(
            of_type = 'integer',
            slot = value,
            value = field['index'],
        ))

        body.append(Verbatim('structinsert {} {} {}'.format(
            result.to_string(),
            key.to_string(),
            value.to_string(),
        )))

        if not field['field'].bare():
            body.append(Ctor(
                of_type = 'atom',
                slot = key,
                value = repr('value'),
            ))
            value_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = value,
                expr = form.value(),
            )
            body.append(Verbatim('structinsert {} {} {}'.format(
                result.to_string(),
                key.to_string(),
                value_slot.to_string(),
            )))

            value_t = sc.type_of(value_slot)
            field_t = viuact.typesystem.t.Value(
                name = str(enum_name),
                templates = (value_t,),
            )
            st.unify_types(enum_t, field_t)

        sc.deallocate_slot(key)
        sc.deallocate_slot(value)

    return result

def emit_primitive_literal(mod, body, st, result, expr):
    lit = expr.value()
    if type(lit) == viuact.lexemes.String:
        body.append(Ctor(
            of_type = 'text',
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
        st.type_of(result, Type.i64())
        return result
    if type(lit) == viuact.lexemes.Bool_literal:
        body.append(Ctor(
            of_type = 'integer',
            slot = result,
            value = ('0' if str(lit) == 'true' else '1'),
        ))
        body.append(Verbatim('not {} {}'.format(
            result.to_string(),
            result.to_string(),
        )))
        st.type_of(result, Type.bool())
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
    with st.scoped() as sc:
        guard_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = guard_slot,
            expr = expr.guard(),
        )

    label_base = '{}+{}+{}'.format(
        mod.name(),
        st.fn(),
        st.special(),
    )
    label_core = hashlib.sha1(label_base.encode('utf-8')).hexdigest()
    label_true = 'if_true_' + label_core
    label_false = 'if_false_' + label_core
    label_end = 'if_end_' + label_core

    body.append(Verbatim('if {} {} {}'.format(
        guard_slot.to_string(),
        label_true,
        label_false,
    )))
    st.deallocate_slot_if_anonymous(guard_slot)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_true)))
    true_arm_t = None
    with st.scoped() as sc:
        slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = (sc.get_anonymous_slot() if result.is_void() else result),
            expr = expr.arm_true(),
        )
        body.append(Verbatim('jump {}'.format(label_end)))
        if not slot.is_void():
            true_arm_t = sc.type_of(slot)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_false)))
    false_arm_t = None
    with st.scoped() as sc:
        slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = (sc.get_anonymous_slot() if result.is_void() else result),
            expr = expr.arm_false(),
        )
        if not slot.is_void():
            false_arm_t = sc.type_of(slot)

    if not Slot.is_void(result):
        st.unify_types(true_arm_t, false_arm_t)
    # sig = mod.signature(st.fn())
    # m, template_parameters = true_arm_t.match(false_arm_t, {})
    # if (not result.is_void()) and (true_arm_t != false_arm_t):
    #     # FIXME viuact.forms.If should record first token pointing to the if
    #     raise viuact.errors.If_arms_return_different_types(
    #         expr.first_token().at(),
    #         true_arm_t,
    #         false_arm_t,
    #     )

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_end)))

    st.actual_pressure(Register_set.LOCAL)

    return result

def emit_match(mod, body, st, result, expr):
    if not expr.arms():
        raise viuact.errors.Match_with_no_arms(
            expr.first_token().at(),
        )

    guard_slot = st.get_slot(name = None)
    with st.scoped() as sc:
        guard_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = guard_slot,
            expr = expr.guard(),
        )
    guard_t = st.type_of(guard_slot)

    enum_definition = mod.enum(guard_t.name())

    # The guard_key_slot holds the key of the enum produces by the guard
    # expression. It will be compared with keys of the with-clauses ("match
    # arms") to see which expression should be executed.
    guard_key_slot = st.get_slot(name = None)
    body.append(Ctor(
        of_type = 'atom',
        slot = guard_key_slot,
        value = repr('key'),
    ))
    body.append(Verbatim('structat {} {} {}'.format(
        guard_key_slot.to_string(),
        guard_slot.to_string(),
        guard_key_slot.to_string(),
    )))
    guard_key_slot = guard_key_slot.as_pointer()

    # The check_slot is used to hold the result of key comparison between the
    # guard expression and with-claus. It can be safely deallocated after the
    # comparisons are done.
    check_slot = st.get_slot(name = None)

    labelled_arms = []
    for arm in expr.arms():
        n = st.special()

        fmt_base = 'with_clause_{}'.format(n)
        arm_id = hashlib.sha1(fmt_base.encode('utf-8')).hexdigest()
        arm_expression_label = 'with_arm_expr_{}'.format(arm_id)
        arm_condition_label = 'with_arm_cond_{}'.format(arm_id)

        labelled_arms.append({
            'expr_label': arm_expression_label,
            'cond_label': arm_condition_label,
            'id': arm_id,
            'arm': arm,
        })
    done_fmt = 'match_done_{}'
    done_label = done_fmt.format(
        hashlib.sha1(done_fmt.format(st.special()).encode('utf-8')).hexdigest())

    # Emit code that compares enum value's tag to different fields of the enum,
    # and dispatches to appropriate with-clause or throws an error. This error
    # is more like assertion in that it should never be triggered (missing cases
    # should be handled at compile time), but let's leave it there just in case.
    #
    # The loop below emits the comparison code.
    catchall_encountered = False
    for i, arm in enumerate(labelled_arms):
        is_catchall = (str(arm['arm'].tag()) == '_')

        if is_catchall:
            catchall_encountered = True

            body.append(Comment(
                'jump to catch-all with-clause'
            ))
            body.append(Marker(label = arm['cond_label']))
            body.append(Jump(
                label = arm['expr_label'],
            ))
        else:
            body.append(Comment(
                'check for with-clause of {}'.format(arm['arm'].tag())
            ))
            body.append(Marker(label = arm['cond_label']))
            body.append(Ctor(
                of_type = 'integer',
                slot = check_slot,
                value = enum_definition['fields'][str(arm['arm'].tag())]['index'],
            ))
            body.append(Cmp(
                kind = Cmp.EQ,
                slot = check_slot,
                rhs = guard_key_slot,
                lhs = check_slot,
            ))
            body.append(If(
                cond = check_slot,
                if_true = arm['expr_label'],
                if_false = (
                    labelled_arms[i + 1]['cond_label']
                    if (i < (len(labelled_arms) - 1)) else
                    done_label
                ),
            ))

    # This is the error handling code handling that runs in case of unmatched
    # enum values. Should never be run, unless the compiler fucked up and did
    # not find a missing case.
    if True:
        body.append(Comment(
            'trigger an error in case nothing matched'
        ))
        body.append(Ctor(
            of_type = 'atom',
            slot = check_slot,
            value = repr('Match_failed'),
        ))
        body.append(Verbatim('exception {} {} void'.format(
            check_slot.to_string(),
            check_slot.to_string(),
        )))
        body.append(Verbatim('throw {}'.format(
            check_slot.to_string(),
        )))

    # Result slots of match-expressions are not disposable since they have a
    # very real effect - they consume their inputs, and this effect must be
    # enforced. Also, we can't have the result slot cancelled or all hell breaks
    # loose (the compiler crashes, for example).
    if result.is_disposable():
        result = result.as_disposable(False)

    # Emit the code that actually executes the with-clauses after the
    # "supporting" code has already been pushed to the body. Keep the type each
    # arm produces to compare them later - all arms must produce the same type
    # if we want to ensure consistency!
    arm_ts = []
    matched_tags = []
    for i, arm in enumerate(labelled_arms):
        # The markers are needed because the code detecting which arm (or:
        # with-clause) to execute uses them for jump targets.
        body.append(Verbatim(''))

        is_catchall = (str(arm['arm'].tag()) == '_')
        if is_catchall:
            body.append(Comment(
                'expression for catch-all with-clause'
            ))
        else:
            body.append(Comment(
                'expression for with-clause of {}'.format(arm['arm'].tag())
            ))
            matched_tags.append(arm['arm'].tag())
        body.append(Marker(label = arm['expr_label']))

        with st.scoped() as sc:
            # Remember to extract the "payload" of the enum value if the arm is
            # not bare, ie. if it provides a name to which the payload value
            # shall be bound.
            if not arm['arm'].bare():
                body.append(Ctor(
                    of_type = 'atom',
                    slot = check_slot,
                    value = Ctor.TAG_ENUM_VALUE_FIELD,
                ))
                value_slot = sc.get_slot(name = str(arm['arm'].name()))
                # Why use structuremove instead of structat instruction? Because
                # we consider the enum value to be "consumed" after the match
                # expression. If the programmer wants to avoid this they can
                # always copy the value before matching it.
                body.append(Verbatim('structremove {} {} {}'.format(
                    value_slot.to_string(),
                    guard_slot.to_string(),
                    check_slot.to_string(),
                )))

                temp_t = guard_t.templates()[0]
                sc.type_of(value_slot, temp_t)

            arm_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = (sc.get_slot(None) if result.is_void() else result),
                expr = arm['arm'].expr(),
            )
            arm_ts.append(sc.type_of(arm_slot))

        # A jump after the last with-clause would be redundant and would cause
        # the assembler to complain about "useless jump" so let's not emit it.
        if i == (len(labelled_arms) - 1):
            continue
        body.append(Jump(label = done_label))
    body.append(Marker(label = done_label))
    body.append(Verbatim(''))

    if len(matched_tags) != len(enum_definition['fields']):
        matched_fields = list(map(lambda _: str(_), matched_tags))
        for field in enum_definition['fields'].values():
            field = field['field']
            if ((str(field.name()) not in matched_fields) and not
                    catchall_encountered):
                raise viuact.errors.Missing_with_clause(
                    expr.guard().first_token().at(),
                    str(field.name()),
                    str(guard_t.name()),
                )

        already_matched = []
        for field in matched_tags:
            if str(field) in already_matched:
                raise viuact.errors.Duplicated_with_clause(
                    field.tok().at(),
                    str(field),
                    str(guard_t.name()),
                )
            already_matched.append(str(field))

        if not catchall_encountered:
            raise viuact.errors.Mismatched_with_clauses(
                expr.guard().first_token().at(),
                str(guard_t.name()),
            )

    # Remember to compare types returned by each arm. They must all be the same!
    if not result.is_void():
        i = 1
        while i < len(arm_ts):
            a = arm_ts[i - 1]
            b = arm_ts[i]

            try:
                st.unify_types(a, b)
            except viuact.typesystem.state.Cannot_unify as e:
                a_t, b_t = e.args
                raise viuact.errors.Type_mismatch(
                    expr.arms()[i].tag().tok().at(),
                    a_t,
                    b_t,
                ).note('between tags {} and {}'.format(
                    str(expr.arms()[i - 1].tag()),
                    str(expr.arms()[i].tag()),
                )).note('all with-clauses must return the same type')

            i += 1

        st.type_of(result, arm_ts[0])

    st.deallocate_slot(check_slot)
    st.deallocate_slot(guard_key_slot)

    # The guard slot value is consumed. If it was a variable it is destroyed and
    # shall not be available after the match-expression that consumed it.
    #
    # FIXME It would be *INCREDIBLY* useful to record the place and reason of
    # deallocation of a slot (and its associated value) to provide better error
    # messages -- see what Rust's compiler is able to do (or look at newer GCC
    # and Clang).
    st.deallocate_slot(guard_slot)
    # st.deallocate_slot_if_anonymous(guard_slot)

    # raise None
    return result

def emit_fn_ref(mod, body, st, result, expr):
    fn_name = str(expr.name())
    candidates = list(filter(
        lambda x: x[1]['base_name'] == fn_name,
        mod.fns(),
    ))

    # We can assume that there is always at least one candidate because this
    # function's only caller is emit_name_ref() - which calls it when it detects
    # that the name to be emitted is a name of a function.
    the_one = None
    if len(candidates) == 1:
        the_one = candidates[0][1]
    else:
        raise None  # FIXME handle more than one candidate

    fn_full_name = '{}/{}'.format(fn_name, the_one['arity'])
    body.append(Verbatim('function {} {}'.format(
        result.to_string(),
        fn_full_name,
    )))
    fn_sig = mod.signature(fn_full_name)

    parameter_types = []
    tmp = {}
    for each in fn_sig['template_parameters']:
        tmp[viuact.typesystem.t.Template(each.name()[1:])] = st.register_template_variable(each)
    for each in fn_sig['parameters']:
        if type(each) is viuact.typesystem.t.Value:
            parameter_types.append(each.concretise(tmp))
        elif type(each) is viuact.typesystem.t.Fn:
            parameter_types.append(each.concretise(tmp))
        elif type(each) is viuact.typesystem.t.Template:
            parameter_types.append(each.concretise(tmp))
        else:
            raise None

    st.type_of(result, viuact.typesystem.t.Fn(
        rt = fn_sig['return'].concretise(tmp),
        pt = tuple(parameter_types),
        templates = tuple(tmp.values()),
    ))

    return result

def emit_name_ref(mod, body, st, result, expr):
    if any(map(lambda x: x[1]['base_name'] == str(expr.name()), mod.fns())):
        return emit_fn_ref(mod, body, st, result, expr)

    if result.is_void():
        viuact.util.log.raw('void slot for name-ref to {}'.format(
            str(expr.name()),
        ))
        raise None
    if result.is_disposable():
        # viuact.util.log.raw('cancelled disposable slot {} for name-ref to {}'.format(
        #     result.to_string(),
        #     str(expr.name()),
        # ))
        st.cancel_slot(result)
        return st.slot_of(str(expr.name())).inhibit_dereference(result.inhibit_dereference())
    else:
        slot = st.slot_of(str(expr.name()))
        # viuact.util.log.raw('move to {} from {} for name-ref to {}'.format(
        #     result.to_string(),
        #     slot.to_string(),
        #     str(expr.name()),
        # ))
        t = st.type_of(slot)
        st.name_slot(result, str(expr.name()))
        if result.inhibit_dereference():
            # viuact.util.log.raw('name-ref creates a pointer: {} <- {}'.format(
            #     result.to_string(),
            #     slot.to_string(),
            # ))
            st.type_of(result, viuact.typesystem.t.Pointer(t))
            body.append(Move.make_pointer(
                source = slot,
                dest = result,
            ))
        else:
            st.type_of(result, t)
            st.deallocate_slot(slot)
            body.append(Move.make_move(
                source = slot,
                dest = result,
            ))
        return result

def emit_throw(mod, body, st, result, expr):
    with st.scoped() as sc:
        ex = mod.exception(expr.tag())

        if ex and expr.bare():
            raise viuact.errors.Invalid_arity(
                pos = expr.tag().tok().at(),
                s = str(expr.tag()),
                kind = viuact.errors.Invalid_arity.EX_CTOR,
            ).note(
                'value is expected'
            ).note(
                '(throw {ex} <value>) instead of (throw {ex})'.format(
                    ex = str(expr.tag()),
                ),
            )

        if not ex and not expr.bare():
            raise viuact.errors.Invalid_arity(
                pos = expr.tag().tok().at(),
                s = str(expr.tag()),
                kind = viuact.errors.Invalid_arity.EX_CTOR,
            ).note(
                '{} is a bare exception'.format(str(expr.tag()))
            )

        value = Slot.make_void()
        if not expr.bare():
            value = sc.get_slot(None)
            value = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = value,
                expr = expr.value(),
            )

        tag = sc.get_slot(None)
        body.append(Ctor(
            of_type = 'atom',
            slot = tag,
            value = repr(str(expr.tag())),
        ))

        if result.is_void():
            result = sc.get_slot(None)

        body.append(Verbatim('exception {} {} {}'.format(
            result.to_string(),
            tag.to_string(),
            value.to_string(),
        )))
        body.append(Verbatim('throw {}'.format(
            result.to_string(),
        )))
        body.append(Verbatim(''))
    return result

def emit_catch_arm(mod, body, st, result, expr):
    exception_slot = (
        st.get_slot(None)
        if expr.bare() else
        st.get_slot(name = str(expr.name()))
    )

    ex_t = mod.exception(str(expr.tag()))
    if (not expr.bare()) and ex_t is None:
        raise viuact.errors.Bind_of_exception_with_no_value(
            expr.first_token().at(),
            expr.tag(),
            expr.name(),
        )

    body.append(Verbatim('draw {}'.format(exception_slot.to_string())))

    if expr.bare():
        body.append(Verbatim('delete {}'.format(exception_slot.to_string())))
        st.deallocate_slot(exception_slot)
        exception_slot = Slot.make_void()
    else:
        body.append(Verbatim('exception_value {ex} {ex}'.format(
            ex = exception_slot.to_string(),
        )))
        st.type_of(exception_slot, viuact.typesystem.t.Value(
            name = str(ex_t.name()),
        ))

    result_slot = emit_expr(
        mod = mod,
        body = body,
        st = st,
        result = result,
        expr = expr.expr(),
    )
    body.append(Verbatim('leave'))

    return result_slot

def emit_try(mod, body, st, result, expr):
    if not expr.arms():
        raise viuact.errors.Try_with_no_arms(
            expr.first_token().at(),
        )

    try_arm_id = hashlib.sha1(
        'try_arm_{}'.format(st.special()).encode('utf-8')).hexdigest()
    try_arm_name = 'try_arm_{}'.format(try_arm_id)

    arms = []
    for arm in expr.arms():
        fmt_base = 'catch_arm_{}'.format(st.special())
        arm_id = hashlib.sha1(fmt_base.encode('utf-8')).hexdigest()
        arm_name = 'catch_arm_{}'.format(arm_id)
        arms.append({
            'exception': arm.tag(),
            'block_id': arm_name,
            'expression': arm,
        })

    body.append(Verbatim('try'))

    for arm in arms:
        body.append(Verbatim('catch {} .block: {}'.format(
            repr(str(arm['exception'])),
            arm['block_id'],
        )))
        with st.scoped() as sc:
            emit_catch_arm(
                mod = mod,
                body = body,
                st = sc,
                result = result,
                expr = arm['expression'],
            )
        body.append(Verbatim('.end'))

    body.append(Verbatim('enter .block: {}'.format(try_arm_name)))
    result = emit_expr(
        mod = mod,
        body = body,
        st = st,
        result = result,
        expr = expr.guard(),
    )
    body.append(Verbatim('leave'))
    body.append(Verbatim('.end'))

    return result

def emit_record_ctor(mod, body, st, result, expr):
    record_type = expr.name()

    body.append(Ctor(
        of_type = 'struct',
        slot = result,
        value = '',
    ))
    st.type_of(result, viuact.typesystem.t.Value(
        name = str(record_type.name()),
    ))

    record_definition = mod.record(record_type.name())

    with st.scoped() as sc:
        field_name = sc.get_slot(None)
        field_value = sc.get_slot(None)

        for each in expr.fields():
            r = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = field_value,
                expr = each.value(),
            )

            r_t = sc.type_of(r)
            # FIXME fix this ugliness and store field types properly, as types,
            # and not as strings
            field_t = str(record_definition['fields'][str(each.name())])
            if field_t == 'i8':
                field_t = Type.i8()
            elif field_t == 'i16':
                field_t = Type.i16()
            else:
                field_t = viuact.typesystem.t.Value(
                    name = field_t,
                )
            try:
                st.unify_types(field_t, r_t)
            except viuact.typesystem.state.Cannot_unify:
                raise viuact.errors.Bad_type_of_record_field(
                    pos = each.value().first_token().at(),
                    record = str(record_type.name()),
                    field = str(each.name()),
                    declared = field_t.to_string(),
                    actual = r_t.to_string(),
                )


            body.append(Ctor(
                of_type = 'atom',
                slot = field_name,
                value = repr(str(each.name())),
            ))
            body.append(Verbatim('structinsert {} {} {}'.format(
                result.to_string(),
                field_name.to_string(),
                field_value.to_string(),
            )))

    return result

def emit_record_field_access(mod, body, st, result, expr):
    with st.scoped() as sc:
        base = sc.get_disposable_slot()
        base = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = base,
            expr = expr.base(),
        )

        record_t = sc.type_of(base)
        pointered_base = (type(record_t) is viuact.typesystem.t.Pointer)
        record_definition = (
            mod.record(record_t.to().name())
            if pointered_base
            else mod.record(record_t.name())
        )

        field = sc.get_slot(None)
        body.append(Ctor(
            of_type = 'atom',
            slot = field,
            value = repr(str(expr.field())),
        ))
        # FIXME use structremove and consume fields if possible (try to detect
        # such opportunities); copying is expensive
        body.append(Verbatim('structat {} {} {}'.format(
            result.to_string(),
            (base.as_pointer() if pointered_base else base).to_string(),
            field.to_string(),
        )))

        field_t = viuact.typesystem.t.Value(
            name = str(record_definition['fields'][str(expr.field())]),
        )
        if result.inhibit_dereference():
            field_t = viuact.typesystem.t.Pointer(field_t)

        # FIXME register the type in case of templates
        st.type_of(result, field_t)
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
    if type(expr) is viuact.forms.Operator_call:
        return emit_operator_call(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
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
        try:
            return emit_name_ref(mod, body, st, result, expr)
        except KeyError:
            raise viuact.errors.Read_of_unbound_variable(
                expr.name().tok().at(),
                str(expr.name()),
            )
    if type(expr) is viuact.forms.Let_binding:
        if not result.is_void():
            st.cancel_slot(result)
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
    if type(expr) is viuact.forms.Enum_ctor_call:
        return emit_enum_ctor_call(
            mod = mod,
            body = body,
            st = st,
            result = result,
            form = expr,
        )
    if type(expr) is viuact.forms.Match:
        return emit_match(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Throw:
        return emit_throw(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Try:
        return emit_try(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Record_ctor:
        return emit_record_ctor(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Record_field_access:
        return emit_record_field_access(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Inhibit_dereference:
        return emit_expr(
            mod = mod,
            body = body,
            st = st,
            result = result.inhibit_dereference(True),
            expr = expr.expr(),
        )
    viuact.util.log.fixme('failed to emit expression: {}'.format(
        typeof(expr)))
    raise None

def cc_fn(mod, fn):
    viuact.util.log.debug('cc.fn: {}::{}/{}'.format(
        mod.name(),
        fn.name(),
        len(fn.parameters()),
    ))

    fn_name = '{}/{}'.format(fn.name(), len(fn.parameters()))
    main_fn_name = (
        '{}::{}'.format(mod.name(), fn_name)
        if mod.name() != EXEC_MODULE else
        fn_name)
    signature = mod.signature(fn_name)

    types = viuact.typesystem.state.State()
    blueprint = {}
    for each in signature['template_parameters']:
        t = viuact.typesystem.t.Template(each.name()[1:])
        blueprint[t] = types.register_type(t)
    st = State(fn = main_fn_name, types = types)

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
        param = signature['parameters'][i].concretise(blueprint)
        st.type_of(dest, param)
        main_fn.append(Move.make_move(
            source = source,
            dest = dest,
        ))

    result_slot = Slot(None, 0, Register_set.LOCAL)
    st.insert_allocated(result_slot)
    st.mark_permanent(result_slot)
    try:
        result = emit_expr(
            mod = mod,
            body = main_fn,
            st = st,
            result = result_slot,
            expr = fn.body(),
        )
    except Exception:
        viuact.util.log.error('during compilation of {}'.format(main_fn_name))
        viuact.util.log.error('dumping body emitted so far')
        for each in main_fn.body:
            viuact.util.log.raw(each.to_string())
        raise
    if result != result_slot:
        main_fn.append(Move.make_move(
            dest = result_slot,
            source = result,
        ))

    try:
        return_t = signature['return'].concretise(blueprint)
        st.unify_types(return_t, st.type_of(result))
    except viuact.typesystem.state.Cannot_unify:
        raise viuact.errors.Bad_returned_type(
            (0, 0,),  # FIXME add position
            # signature['return'],
            fn_name,
            signature['return'],
            st.type_of(result),
        )
        raise 0

    try:
        # st._types.dump()
        pass
    except RecursionError:
        viuact.util.log.error(
            'a type refers to itself (check template variables dump)')
        raise viuact.errors.Fail(
            (0, 0,),
            'infinite loop encountered during type dump'
        )

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
    if type(form) is viuact.forms.Type_name:
        name = str(form.name())

        if name[0] == "'":
            return viuact.typesystem.t.Template(
                name = name[1:],
            )
        elif name == 'void':
            return viuact.typesystem.t.Void()
        else:
            parameters = [cc_type(mod, each) for each in form.parameters()]
            return viuact.typesystem.t.Value(
                name = name,
                templates = tuple(parameters),
            )
    if type(form) is viuact.forms.Fn_type:
        return_type = cc_type(mod, form.return_type())
        parameter_types = []
        for x in form.parameter_types():
            parameter_types.append(cc_type(mod, x))

        return viuact.typesystem.t.Fn(
            rt = return_type,
            pt = tuple(parameter_types),
            templates = (),
        )
    viuact.util.log.error('cannot compile type from: {} [{}]'.format(
        str(form),
        typeof(form),
    ))
    raise viuact.errors.Internal_compiler_error()


def signature_to_string(full_name, sig):
    tp = sig['template_parameters']
    fp = sig['parameters']
    rt = sig['return']

    fmt = '(val {name} ({fp}) -> {rt})'
    if tp:
        fmt = '(val ({tp}) {name} ({fp}) -> {rt})'

    template_parameters = ' '.join(map(lambda x: x.to_string(), tp))

    formal_parameters = ' '.join(map(lambda x: x.to_string(), fp))
    return_type = rt.to_string()

    return fmt.format(
        tp = template_parameters,
        name = full_name,
        fp = formal_parameters,
        rt = return_type,
    )

INDENT = '    '

def signature_of_enum_to_string(name, sig, indent):
    fmt = '(enum {} (\n{}\n))'

    fields = []
    for f, v in sorted(sig['fields'].items(), key = lambda x: x[1]['index']):
        if v['field'].bare():
            fields.append((INDENT * (indent + 1)) + '{}'.format(f))
        else:
            fields.append((INDENT * (indent + 1)) + '({} {})'.format(f, v['field'].value()))

    return fmt.format(name, '\n'.join(fields))

def signature_of_record_to_string(name, sig, indent):
    fmt = '(type {} {{\n{}\n}})'

    fields = []
    viuact.util.log.raw(sig)
    for f, v in sig['fields'].items():
        fields.append((INDENT * (indent + 1)) + '(val {} {})'.format(
            f,
            str(v),
        ))

    return fmt.format(name, '\n'.join(fields))


def cc_impl_prepare_module(module_name, source_file, forms):
    mod = Module_info(module_name, source_file)

    for each in filter(lambda x: type(x) is viuact.forms.Enum, forms):
        mod.make_enum(
            name = each.name(),
            fields = each.fields(),
            template_parameters = [
                viuact.typesystem.t.Template(
                    name = str(t)[1:],
                )
                for t
                in each.template_parameters()
            ],
        )

    for each in filter(lambda x: type(x) is viuact.forms.Record_definition, forms):
        mod.make_record(
            name = each.tag(),
            fields = each.fields(),
        )

    for each in filter(lambda x: type(x) is viuact.forms.Exception_definition, forms):
        mod.make_exception(
            tag = each.tag(),
            value = each.value(),
        )

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

    return mod

def cc_impl_emit_functions(mod, forms):
    fns = []

    for each in filter(lambda x: type(x) is viuact.forms.Fn, forms):
        out = cc_fn(mod, each)
        fns.append({ 'name': out.main.name, 'out': out, 'raw': each, })

    return fns

def cc_impl_save_implementation(mod, fns, build_directory, output_file):
    with open(os.path.join(build_directory, output_file), 'w') as ofstream:
        print = lambda s: ofstream.write('{}\n'.format(s))
        print(';')
        if mod.name() == EXEC_MODULE:
            print('; Function definitions')
        else:
            print('; Function definitions for module {}'.format(mod.name()))
        print(';')

        for each in fns:
            out = each['out']

            print('')

            sig = mod.signature(out.main.name.split('::')[-1])
            print('; {}'.format(signature_to_string(out.main.name.split('/')[0], sig)))

            print('.function: {}'.format(out.main.name))
            for line in out.main.body:
                print('    {}'.format(line.to_string()))
            print('.end')

def cc_impl_save_interface(mod, file_paths, roots):
    source_file, output_file = file_paths
    source_root, build_directory = roots

    src_interface_file = '{}.vti'.format(source_file.rsplit('.', maxsplit=1)[0])
    out_interface_file = '{}.vti'.format(output_file.rsplit('.', maxsplit=1)[0])
    if os.path.isfile(os.path.join(source_root, src_interface_file)):
        shutil.copyfile(
            src = os.path.join(source_root, src_interface_file),
            dst = os.path.join(build_directory, out_interface_file),
        )
        return

    out_interface_path = os.path.join(build_directory, out_interface_file)
    with open(out_interface_path, 'w') as ofstream:
        print = lambda s: ofstream.write('{}\n'.format(s))
        print(';')
        print('; This interface file was automatically generated.')
        print(';')

        print('')
        for each in mod.enums():
            sig = mod.enum(each)
            print(signature_of_enum_to_string(each, sig, 0))

        print('')
        for each in mod.records():
            sig = mod.record(each)
            print(signature_of_record_to_string(each, sig, 0))

        print('')
        for each in mod.fns(local = True):
            fn, _ = each
            sig = mod.signature(fn)
            print(signature_to_string(sig['base_name'], sig))

def cc(source_root, source_file, module_name, forms, build_directory):
    base_output_file = (os.path.splitext(source_file)[0] + '.asm')
    output_file = os.path.normpath(base_output_file)

    viuact.util.log.debug('cc: [{}]/{} -> {}/{}'.format(
        source_root,
        source_file,
        build_directory,
        output_file,
    ))

    mod = cc_impl_prepare_module(module_name, source_file, forms)
    fns = cc_impl_emit_functions(mod, forms)

    output_directory = os.path.split(os.path.join(build_directory, output_file))[0]
    os.makedirs(output_directory, exist_ok = True)

    cc_impl_save_implementation(mod, fns, build_directory, output_file)
    cc_impl_save_interface(
        mod,
        (source_file, output_file,),
        (source_root, build_directory,),
    )
