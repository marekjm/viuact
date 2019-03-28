from viuact import token_types


class Group_type:
    def __repr__(self):
        s = self.to_string()
        return '{}{}{}'.format(
            self.type_name,
            (': ' if s else ''),
            s,
        )

    def to_content(self):
        return None

    def to_data(self):
        return {
            'data': self.to_content(),
            'type': self.type_name,
        }


class Inline_module(Group_type):
    type_name = 'Inline_module'

    def __init__(self, name):
        self.name = name
        self.functions = {}
        self.function_names = []
        self.modules = {}
        self.module_names = []
        self.imports = []
        self.enums = []

    def to_string(self):
        s = ', '.join(map(lambda each: each.to_string(), self.functions.values()))
        return '{} with {}'.format(
            str(self.name.token),
            (s or 'no functions'),
        )

    def to_content(self):
        return {
            'name': self.name.to_data(),
            'functions': dict([(name, fn.to_data(),) for name, fn in self.functions.items()]),
            'function_names': self.function_names,
            'modules': dict([(name, mod.to_data(),) for name, mod in self.modules.items()]),
            'module_names': self.module_names,
            'imports': self.imports,
        }


class Module(Group_type):
    type_name = 'Module'

    def __init__(self, name):
        self.name = name

    def to_string(self):
        return self.name.token

    def to_content(self):
        return {
            'name': self.name.to_data(),
        }


class Enum_definition(Group_type):
    type_name = 'Enum_definition'

    def __init__(self, name, values):
        self.name = name
        self.values = values

    def to_string(self):
        s = ', '.join(map(lambda each: str(each.token), self.values))
        return 'enum {} ({})'.format(
            str(self.name.token),
            s
        )

    def to_content(self):
        return {
            'name': self.name.to_data(),
            'values': [each.to_data() for each in self.values],
        }


class Function(Group_type):
    type_name = 'Function'

    def __init__(self, name):
        self.name = name
        self.arguments = []
        self.body = []

    def to_string(self):
        return '{}({})'.format(
            str(self.name.token),
            ', '.join(map(lambda each: str(each.token), self.arguments)),
        )

    def to_content(self):
        return {
            'name': self.name.to_data(),
            'arguments': [each.to_data() for each in self.arguments],
            'body': [each.to_data() for each in self.body],
        }


class Import(Group_type):
    type_name = 'Import'

    def __init__(self, name):
        self.name = name

    def to_string(self):
        return self.name.to_string()

    def to_content(self):
        return {
            'target': self.name.to_data(),
        }


class Let_binding(Group_type):
    type_name = 'Let_binding'

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def to_string(self):
        return '{} = {}'.format(
            str(self.name.token),
            str(self.value),
        )

    def to_content(self):
        return {
            'name': self.name.to_data(),
            'value': self.value.to_data(),
        }


class Function_call(Group_type):
    type_name = 'Function_call'

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def to(self):
        return (str(self.name.token) if type(self.name) is token_types.Name else self.name.to_string())

    def to_string(self):
        return '{}({})'.format(
            self.to(),
            ', '.join(map(str, self.args)),
        )

    def to_content(self):
        return {
            'to': self.name.to_data(),
            'args': [each.to_data() for each in self.args],
        }


class Operator_call(Group_type):
    type_name = 'Operator_call'

    def __init__(self, operator, args):
        self.operator = operator
        self.args = args

    def to(self):
        return (str(self.operator.token)
                if (type(self.operator) in token_types.OPERATOR_TYPES)
                else self.operator.to_string())

    def to_string(self):
        return '{}({})'.format(
            self.to(),
            ', '.join(map(str, self.args)),
        )

    def to_content(self):
        return {
            'operator': self.operator.to_data(),
            'args': [each.to_data() for each in self.args],
        }


class Actor_call(Group_type):
    type_name = 'Actor_call'

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def to(self):
        return (str(self.name.token) if type(self.name) is token_types.Name else self.name.to_string())

    def to_string(self):
        return 'actor {}({})'.format(
            self.to(),
            ', '.join(map(str, self.args)),
        )

    def to_content(self):
        return Function_call.to_content(self)


class Tail_call(Group_type):
    type_name = 'Tail_call'

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def to(self):
        return (str(self.name.token) if type(self.name) is token_types.Name else self.name.to_string())

    def to_string(self):
        return 'tailcall {}({})'.format(
            self.to(),
            ', '.join(map(str, self.args)),
        )

    def to_content(self):
        return Function_call.to_content(self)


class Deferred_call(Group_type):
    type_name = 'Deferred_call'

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def to(self):
        return (str(self.name.token) if type(self.name) is token_types.Name else self.name.to_string())

    def to_string(self):
        return 'defer {}({})'.format(
            self.to(),
            ', '.join(map(str, self.args)),
        )

    def to_content(self):
        return Function_call.to_content(self)


class Watchdog_call(Group_type):
    type_name = 'Watchdog_call'

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def to(self):
        return (str(self.name.token) if type(self.name) is token_types.Name else self.name.to_string())

    def to_string(self):
        return 'defer {}({})'.format(
            self.to(),
            ', '.join(map(str, self.args)),
        )

    def to_content(self):
        return Function_call.to_content(self)


class Try_expression(Group_type):
    type_name = 'Try_expression'

    def __init__(self, expr, handling_blocks):
        self.expr = expr
        self.handling_blocks = handling_blocks

    def to_string(self):
        return 'try {} with ...'.format(
            self.expr.to_string(),
        )

    def to_content(self):
        return {
            'expr': self.expr.to_data(),
            'handling_blocks': list(map(lambda each: each.to_data(), self.handling_blocks)),
        }


class Catch_expression(Group_type):
    type_name = 'Catch_expression'

    def __init__(self, tag, name, expr):
        self.tag = tag
        self.name = name
        self.expr = expr

    def to_string(self):
        return '{} {} {}'.format(
            self.tag.to_string(),
            str(self.name.token),
            (self.expr.to_string() if isinstance(self.expr, Group_type) else '...'),
        )

    def to_content(self):
        return {
            'tag': self.tag.to_data(),
            'name': self.name.to_data(),
            'expr': self.expr.to_data(),
        }


class Exception_tag(Group_type):
    type_name = 'Exception_tag'

    def __init__(self, tag):
        self.tag = tag

    def to_string(self):
        return '{}'.format(
            str(self.tag),
        )

    def to_content(self):
        return {
            'tag': str(self.tag),
        }


class Name_ref(Group_type):
    type_name = 'Name_ref'

    def __init__(self, name):
        self.name = name

    def to_string(self):
        return '{}'.format(
            str(self.name.token),
        )

    def to_content(self):
        return {
            'name': self.name.to_data(),
        }


class Id(Group_type):
    type_name = 'Id'

    def __init__(self, name):
        self.name = name

    def to_string(self):
        return ''.join(
            map(lambda each: ('::' if each == '.' else each),
            map(lambda each: str(each.token), self.name)))

    def to_content(self):
        return {
            'id': [each.to_data() for each in self.name],
        }


class If(Group_type):
    type_name = 'If'

    def __init__(self, condition, arms):
        self.condition = condition
        self.arms = arms

    def to_string(self):
        return 'if ({})'.format(self.condition)

    def to_content(self):
        return {
            'condition': self.condition.to_data(),
            'true_arm': self.arms[0].to_data(),
            'false_arm': self.arms[1].to_data(),
        }


class Compound_expression(Group_type):
    type_name = 'Compound_expression'

    def __init__(self, expressions):
        self.expressions = expressions

    def to_string(self):
        return '({})'.format(' '.join(map(
            (lambda x: '({})'.format(x.to_string() if isinstance(x, Group_type) else str(x))),
            self.expressions
        )))

    def to_content(self):
        return {
            'expressions': [each.to_data() for each in self.expressions],
        }


class Struct(Group_type):
    type_name = 'Struct'

    def __init__(self):
        pass

    def to_string(self):
        return 'struct'


class Vector(Group_type):
    type_name = 'Vector'

    def __init__(self):
        pass

    def to_string(self):
        return 'vector'


class Field_assignment(Group_type):
    type_name = 'Field_assignment'

    def __init__(self, operator, field, value):
        self.operator = operator
        self.field = field
        self.value = value

    def to_string(self):
        return '{} := ...'.format(
            ''.join(map(lambda each: str(each.token), self.field)),
        )

    def to_content(self):
        return {
            'operator': self.operator.to_data(),
            'field': [each.to_data() for each in self.field],
            'value': self.value.to_data(),
        }


class Pointer_dereference(Group_type):
    type_name = 'Pointer_dereference'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return '^ {}'.format(self.value.to_string())

    def to_content(self):
        return {
            'value': self.value.to_data(),
        }
