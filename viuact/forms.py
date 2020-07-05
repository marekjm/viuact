import enum


class Form:
    forms = []


class Fn(Form):
    def __init__(self, name, parameters, expression):
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
        self._name = name   # lexeme
        self._value = value # form

    def val(self):
        return self._value

class Argument_bind(Form):
    def __init__(self, name, value):
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
        self._to = to                   # G
        self._arguments = arguments     # [form]
        self._kind = kind               # Kind

    def to(self):
        return self._to

    def arguments(self):
        return self._arguments

class Primitive_literal(Form):
    def __init__(self, value):
        self._value = value  # lexeme

    def value(self):
        return self._value

class Name_ref(Form):
    def __init__(self, name):
        self._name = name  # lexeme

    def name(self):
        return self._name

class Let_binding(Form):
    def __init__(self, name, value):
        self._name = name   # lexeme
        self._value = value # form

    def name(self):
        return self._name

    def val(self):
        return self._value

class If(Form):
    def __init__(self, guard, if_true, if_false):
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
]
