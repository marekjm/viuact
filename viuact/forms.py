import enum

import viuact.lexemes


class Form:
    forms = []

    def __init__(self, ft):
        # First token is used to report approximate position of the form inside
        # source file in case it is involved in an error.
        self._first_token = ft

    def first_token(self):
        return self._first_token


class Fn(Form):
    def __init__(self, name, parameters, expression):
        super().__init__(name.tok())
        self._name = name               # lexeme
        self._parameters = parameters   # [form]
        self._expression = expression   # form

    def name(self):
        return self._name

    def parameters(self):
        return self._parameters

    def body(self):
        return self._expression

class Fn_parameter(Form):
    def __init__(self, name):
        super().__init__(name.tok())
        self._name = name   # lexeme

    def __str__(self):
        return str(self._name)

    def name(self):
        return self._name

class Named_parameter(Fn_parameter):
    pass

class Labelled_parameter(Fn_parameter):
    pass

class Defaulted_parameter(Fn_parameter):
    def __init__(self, name, value):
        super().__init__(name.tok())
        self._name = name   # lexeme
        self._value = value # form

    def val(self):
        return self._value

class Argument_bind(Form):
    def __init__(self, name, value):
        super().__init__(name.tok())
        self._name = name   # lexeme
        self._value = value # form

    def name(self):
        return self._name

    def val(self):
        return self._value

class Compound_expr(Form):
    def __init__(self, expressions):
        self._expressions = expressions  # [form]

    def body(self):
        return self._expressions

class Fn_call(Form):
    class Kind(enum.Enum):
        Call     = 0
        Tail     = 1
        Actor    = 2
        Defer    = 3
        Watchdog = 4

    def __init__(self, to, arguments, kind):
        super().__init__(to.first_token())
        self._to = to                   # G
        self._arguments = arguments     # [form]
        self._kind = kind               # Kind

    def callee_name(self):
        callee = self.to()
        if type(callee) is Name_path:
            return '{}::{}'.format(
                '::'.join(map(str, callee.mod())),
                callee.name(),
            )
        elif type(callee) is Name_ref:
            return str(callee.name())
        raise None

    def to(self):
        return self._to

    def arguments(self):
        return self._arguments

class Operator_call(Form):
    def __init__(self, operator, arguments):
        super().__init__(operator.tok())
        self._operator = operator   # viuact.lexemes.Lexeme
        self._arguments = arguments # [Form]

    def operator(self):
        return self._operator

    def arguments(self):
        return self._arguments

class Enum_ctor_path(Form):
    def __init__(self, field, name, module_prefix):
        super().__init__(field)
        self._field = field             # lexemes.Enum_ctor_name
        self._name = name               # lexemes.Name
        self._prefix = module_prefix    # [lexemes.Mod_name]

    def field(self):
        return self._field

    def of_enum(self):
        return self._name

    def module(self):
        if not self._prefix:
            return None
        return '::'.join(map(str, self._prefix))

class Enum_ctor_call(Form):
    def __init__(self, to, value):
        super().__init__(to.first_token())
        self._to = to           # Enum_ctor_path
        self._value = value     # form

    def to(self):
        return self._to

    def value(self):
        return self._value

class Enum_field(Form):
    def __init__(self, name, value):
        super().__init__(name.tok())
        self._name = name       # lexemes.Enum_ctor_name
        self._value = value     # form | None

    def name(self):
        return self._name

    def value(self):
        return self._value

    def bare(self):
        return (self._value is None)

class Enum(Form):
    def __init__(self, name, fields, template_parameters):
        super().__init__(name.tok())
        self._name = name       # lexemes.Name
        self._fields = fields   # [Enum_field]
        self._template_parameters = template_parameters # [form]

    def name(self):
        return self._name

    def fields(self):
        return self._fields

    def template_parameters(self):
        return self._template_parameters

    def bare(self):
        return all(map(lambda x: x.bare(), self.fields()))

class Match_arm(Form):
    def __init__(self, tag, name, expr):
        super().__init__(tag.tok())
        self._tag = tag         # lexemes.Enum_ctor_name
        self._name = name       # lexemes.Name | None
        self._expression = expr # form

    def tag(self):
        return self._tag

    def name(self):
        return self._name

    def bare(self):
        return ((self.name() is None)
                or (type(self.name()) is viuact.lexemes.Drop))

    def expr(self):
        return self._expression

class Match(Form):
    def __init__(self, guard, arms):
        super().__init__(guard.first_token())
        self._guard = guard     # form
        self._arms = arms       # [Match_arm]

    def guard(self):
        return self._guard

    def arms(self):
        return self._arms

class Primitive_literal(Form):
    def __init__(self, value):
        super().__init__(value.tok())
        self._value = value  # lexeme

    def value(self):
        return self._value

class Raw_slot(Form):
    def __init__(self, slot, tok):
        super().__init__(tok)
        self._slot = slot  # Slot

    def slot(self):
        return self._slot

class Name_ref(Form):
    def __init__(self, name):
        super().__init__(name.tok())
        self._name = name  # lexeme

    def name(self):
        return self._name

class Name_path(Form):
    def __init__(self, mod, name):
        super().__init__(name.tok())
        self._mod = mod    # [viuact.lexemes.Mod_name]
        self._name = name  # viuact.lexemes.Name

    def mod(self):
        return self._mod

    def name(self):
        return self._name

class Let_binding(Form):
    def __init__(self, name, value):
        super().__init__(name.tok())
        self._name = name   # lexeme
        self._value = value # form

    def name(self):
        return self._name

    def val(self):
        return self._value

class If(Form):
    def __init__(self, guard, if_true, if_false):
        super().__init__(guard.first_token())
        self._guard = guard         # form
        self._if_true = if_true     # form
        self._if_false = if_false   # form

    def guard(self):
        return self._guard

    def arm(self, value):
        return (self._if_true if value else self._if_false)

    def arm_true(self):
        return self.arm(True)

    def arm_false(self):
        return self.arm(False)

class Val_fn_spec(Form):
    def __init__(self, name, template_parameters, parameter_types, return_type):
        super().__init__(name.tok())
        self._name = name                                # lexeme
        self._template_parameters = template_parameters  # [form]
        self._parameter_types = parameter_types          # [form]
        self._return_type = return_type                  # form

    def name(self):
        return self._name

    def template_parameters(self):
        return self._template_parameters

    def parameter_types(self):
        return self._parameter_types

    def return_type(self):
        return self._return_type

    def to_string(self):
        return '{} ({}) -> {}'.format(
            self.name(),
            ' '.join(map(lambda _: _.to_string(), self.parameter_types())),
            self.return_type().to_string(),
        )

class Type_name(Form):
    def __init__(self, name, template_parameters):
        super().__init__(name.tok())
        self._name = name   # Name
        self._template_parameters = template_parameters

    def name(self):
        return self._name

    def parameters(self):
        return self._template_parameters

    def to_string(self):
        if self.parameters():
            return '(({}) {})'.format(
                ' '.join(map(lambda x: x.to_string(), self.parameters())),
                self.name(),
            )
        else:
            return str(self.name())

class Fn_type(Form):
    def __init__(self, return_type, parameter_types):
        super().__init__(return_type.first_token())
        self._return_type = return_type
        self._parameter_types = parameter_types

    def return_type(self):
        return self._return_type

    def parameter_types(self):
        return self._parameter_types

    def to_string(self):
        return '(({}) -> {})'.format(
            ', '.join(map(lambda x: x.to_string(), self.parameter_types())),
            self.return_type().to_string(),
        )

class Exception_definition(Form):
    def __init__(self, tag, value):
        super().__init__(tag.tok())
        self._name = tag       # lexemes.Exception_name
        self._value = value     # form | None

    def tag(self):
        return self._name

    def value(self):
        return self._value

    def bare(self):
        return (self._value is None)

class Throw(Form):
    def __init__(self, tag, value):
        super().__init__(tag.tok())
        self._tag = tag       # lexemes.Exception_name
        self._value = value     # form | None

    def tag(self):
        return self._tag

    def value(self):
        return self._value

    def bare(self):
        return (self._value is None)

class Try(Form):
    def __init__(self, guard, arms):
        super().__init__(guard.first_token())
        self._guard = guard     # form
        self._arms = arms       # [Catch_arm]

    def guard(self):
        return self._guard

    def arms(self):
        return self._arms

class Catch_arm(Form):
    def __init__(self, tag, name, expr):
        super().__init__(tag.tok())
        self._tag = tag         # lexemes.Exception_name
        self._name = name       # lexemes.Name | None
        self._expression = expr # form

    def tag(self):
        return self._tag

    def name(self):
        return self._name

    def bare(self):
        return ((self.name() is None)
                or (type(self.name()) is viuact.lexemes.Drop))

    def expr(self):
        return self._expression

class Record_definition(Form):
    def __init__(self, tag, fields):
        super().__init__(tag.tok())
        self._tag = tag
        self._fields = fields

    def tag(self):
        return self._tag

    def fields(self):
        return self._fields

class Record_field_definition(Form):
    def __init__(self, name, type):
        super().__init__(name.tok())
        self._name = name  # viuact.lexmes.Name
        self._type = type  # viuact.lexmes.Name

    def name(self):
        return self._name

    def type(self):
        return self._type

class Record_ctor_field(Form):
    def __init__(self, name, value):
        super().__init__(name.tok())
        self._name = name   # viuact.lexmes.Name
        self._value = value # Form

    def name(self):
        return self._name

    def value(self):
        return self._value

class Record_ctor(Form):
    def __init__(self, name, fields):
        if name is not None: # this just for temporary ctor calls
            super().__init__(name.first_token())
        self._name = name       # None | viuact.lexmes.Name
        self._fields = fields   # [Record_ctor_field]

    def name(self):
        return self._name

    def fields(self):
        return self._fields

class Record_field_access(Form):
    def __init__(self, base, field):
        super().__init__(base.first_token())
        self._base = base    # Form
        self._field = field  # Name

    def base(self):
        return self._base

    def field(self):
        return self._field

class Inhibit_dereference(Form):
    def __init__(self, operator, expression):
        super().__init__(operator.tok())
        self._expr = expression

    def expr(self):
        return self._expr

class Import(Form):
    def __init__(self, module):
        super().__init__(module[0].tok())
        self._module = module  # [viuact.lexemes.Mod_name]

    def module(self):
        return self._module

    def path(self):
        return '::'.join(map(str, self.module()))

class Drop(Form):
    def __init__(self, drop):
        super().__init__(drop.tok())


Form.forms = [
    Fn,
    Named_parameter,
    Labelled_parameter,
    Defaulted_parameter,
    Argument_bind,
    Compound_expr,
    Fn_call,
    Primitive_literal,
    Let_binding,
    Exception_definition,
]
