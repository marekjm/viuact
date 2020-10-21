import enum

from viuact.util.type_annotations import T, I, Alt


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
