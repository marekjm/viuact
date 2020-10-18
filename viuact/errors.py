################################################################################
# Base classes for user errors, i.e. errors triggered by invalid user code.
#
class Error(Exception):
    def __init__(self, pos):
        self.line = pos[0]
        self.character = pos[1]
        self._fallout = []
        self._notes = []

    def at(self, human = False):
        return (self.line + int(human), self.character + int(human),)

    def what(self):
        return ' '.join(str(type(self))[8:-2].split('.')[-1].lower().split('_'))

    def then(self, another_error):
        self._fallout.append(another_error)
        return self

    def fallout(self):
        return self._fallout

    def notes(self):
        return self._notes

    def note(self, s):
        self._notes.append(s)
        return self


class Info(Error):
    def __init__(self, pos, m):
        super().__init__(pos)
        self.bad = m

    def what(self):
        return self.bad


class Fail(Error):
    def __init__(self, pos, m):
        super().__init__(pos)
        self.bad = m

    def what(self):
        return self.bad


################################################################################
# Errors that occur during lexical analysis.
#
class Lexer_error(Error):
    pass

class Unexpected_character(Lexer_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), repr(self.bad))


################################################################################
# Errors that occur during syntactical analysis.
#
class Parser_error(Error):
    pass

class Unexpected_token(Lexer_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), repr(self.bad))

class Unbalanced_braces(Lexer_error):
    def __init__(self, pos, s = None):
        super().__init__(pos)
        self.bad = s

    def what(self):
        s = super().what()
        if self.bad is not None:
            s = '{}: unexpected {}'.format(s, repr(str(self.bad)))
        return s

class Invalid_sentinel(Lexer_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), repr(self.bad))


################################################################################
# Errors that occur during code emission.
#
class Emitter_error(Error):
    pass

class Source_cannot_be_void(Emitter_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{} for {}'.format(super().what(), self.bad)

class Invalid_arity(Emitter_error):
    FUNCTION = 'function'
    ENUM_CTOR = 'enum ctor'
    EX_CTOR = 'exception ctor'
    OPERATOR = 'operator'

    def __init__(self, pos, s, kind = FUNCTION):
        super().__init__(pos)
        self.bad = s
        self.kind = kind

    def what(self):
        return '{} in call to {} {}'.format(
            super().what(),
            self.kind,
            self.bad,
        )

class Unknown_function(Emitter_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), self.bad)

class Missing_argument(Emitter_error):
    def __init__(self, pos, fn, arg):
        super().__init__(pos)
        self.fn = fn
        self.arg = arg

    def what(self):
        return '{} for function {}: {}'.format(super().what(), self.fn, self.arg)

class Missing_positional_argument(Missing_argument):
    pass

class Missing_labelled_argument(Missing_argument):
    pass

class No_signature_for_function(Emitter_error):
    def __init__(self, pos, fn):
        super().__init__(pos)
        self.fn = fn

    def what(self):
        return '{} {}'.format(super().what(), self.fn)

class Missing_with_clause(Emitter_error):
    def __init__(self, pos, tag, for_enum):
        super().__init__(pos)
        self.tag = tag
        self.for_enum = for_enum

    def what(self):
        return '{} for tag {} when matching over enum {}'.format(
            super().what(),
            repr(self.tag),
            repr(self.for_enum),
        )

class Duplicated_with_clause(Emitter_error):
    def __init__(self, pos, tag, for_enum):
        super().__init__(pos)
        self.tag = tag
        self.for_enum = for_enum

    def what(self):
        return '{} for tag {} when matching over enum {}'.format(
            super().what(),
            repr(self.tag),
            repr(self.for_enum),
        )

class Mismatched_with_clauses(Emitter_error):
    def __init__(self, pos, for_enum):
        super().__init__(pos)
        self.for_enum = for_enum

    def what(self):
        return '{} when matching over enum {}'.format(
            super().what(),
            repr(self.for_enum),
        )

class Read_of_unbound_variable(Emitter_error):
    def __init__(self, pos, variable):
        super().__init__(pos)
        self.variable = variable

    def what(self):
        return '{}: {}'.format(super().what(), self.variable)

class Record_ctor_received_more_than_one_argument(Emitter_error):
    def __init__(self, pos, name, no_of_args):
        super().__init__(pos)
        self.name = name
        self.no_of_args = no_of_args

    def what(self):
        return 'record constructor for {} expects 1 argument, but received {}'.format(
            self.name,
            self.no_of_args,
        )

class Type_error(Emitter_error):
    pass

class Type_mismatch(Type_error):
    def __init__(self, pos, a, b):
        super().__init__(pos)
        self.a = a
        self.b = b

    def what(self):
        return '{}: {} != {}'.format(super().what(), self.a, self.b)

class Bad_returned_type(Type_error):
    def __init__(self, pos, fn, declared, returned):
        super().__init__(pos)
        self.fn = fn
        self.declared = declared
        self.returned = returned

    def what(self):
        return '{w} from {fn}: returned {ret} != declared {decl}'.format(
            w = super().what(),
            fn = self.fn,
            decl = self.declared,
            ret = self.returned,
        )

class Bad_argument_type(Type_error):
    def __init__(self, pos, fn, i, declared, actual):
        super().__init__(pos)
        self.fn = fn
        self.index = i
        self.declared = declared
        self.actual = actual

    def what(self):
        fmt = '{w} of parameter {i} in call to {fn}: declared {decl} != actual {act}'
        return fmt.format(
            w = super().what(),
            i = self.index,
            fn = self.fn,
            decl = self.declared,
            act = self.actual,
        )

class If_arms_return_different_types(Type_error):
    def __init__(self, pos, true_arm_t, false_arm_t):
        super().__init__(pos)
        self.true_arm_t = true_arm_t    # Type.t
        self.false_arm_t = false_arm_t  # Type.t

    def what(self):
        fmt = '{w}: {t} and {f}'
        return fmt.format(
            w = super().what(),
            t = self.true_arm_t,
            f = self.false_arm_t,
        )

class Match_with_no_arms(Type_error):
    def __init__(self, pos):
        super().__init__(pos)

class Try_with_no_arms(Type_error):
    def __init__(self, pos):
        super().__init__(pos)

class Read_of_void(Type_error):
    def __init__(self, pos, by : str):
        super().__init__(pos)
        self.by = by

    def what(self):
        return '{} by {}'.format(super().what(), self.by)

class Bind_of_exception_with_no_value(Type_error):
    def __init__(self, pos, ex : str, to : str):
        super().__init__(pos)
        self.ex = ex
        self.to = to

    def what(self):
        return '{}: {} to name {}'.format(super().what(), self.ex, self.to)

class Bad_type_of_record_field(Type_error):
    def __init__(self, pos, record, field, declared, actual):
        super().__init__(pos)
        self.record = record
        self.field = field
        self.declared = declared
        self.actual = actual

    def what(self):
        fmt = 'bad type for field {f} of record {r}: declared {decl} != actual {act}'
        return fmt.format(
            f = self.field,
            r = self.record,
            decl = self.declared,
            act = self.actual,
        )


################################################################################
# Errors that occur if the compiler as a bug.
#
class Internal_compiler_error(Exception):
    def __init__(self):
        self.pos = None

    def what(self):
        return 'ICE: {}'.format(
            ' '.join(str(type(self))[8:-2].split('.')[-1].lower().split('_')))

class Mutation_of_inactive_state(Internal_compiler_error):
    pass

class Double_deallocation(Internal_compiler_error):
    def __init__(self, slot):
        self.slot = slot

    def __str__(self):
        return '{} of slot {}'.format(self.what(), self.slot.to_string())

class Double_cancel(Internal_compiler_error):
    def __init__(self, slot):
        self.slot = slot

    def __str__(self):
        return '{} of slot {}'.format(self.what(), self.slot.to_string())

class Cancel_of_deallocated(Internal_compiler_error):
    def __init__(self, slot):
        self.slot = slot

    def __str__(self):
        return '{} of slot {}'.format(self.what(), self.slot.to_string())

class Deallocation_of_cancelled(Internal_compiler_error):
    def __init__(self, slot):
        self.slot = slot

    def __str__(self):
        return '{} of slot {}'.format(self.what(), self.slot.to_string())

class Read_of_untyped_slot(Internal_compiler_error):
    def __init__(self, slot):
        self.slot = slot

    def __str__(self):
        return '{}: {}'.format(self.what(), self.slot.to_string())

class Feature_not_implemented(Internal_compiler_error):
    def __init__(self, feature):
        self.feature = feature

    def __str__(self):
        return '{}: {}'.format(self.what(), self.feature)
