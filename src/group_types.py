import token_types


class Group_type:
    def __repr__(self):
        s = self.to_string()
        return '{}{}{}'.format(
            self.type_name,
            (': ' if s else ''),
            s,
        )


class Module(Group_type):
    type_name = 'Module'

    def __init__(self, name):
        self.name = name
        self.functions = {}
        self.function_names = []
        self.modules = {}
        self.module_names = []

    def to_string(self):
        s = ', '.join(map(lambda each: each.to_string(), self.functions.values()))
        return '{} with {}'.format(
            str(self.name.token),
            (s or 'no functions'),
        )


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


class Operator_call(Group_type):
    type_name = 'Operator_call'

    def __init__(self, operator, args):
        self.operator = operator
        self.args = args

    def to(self):
        return (str(self.operator.token)
                if isinstance(self.operator, (token_types.Logic_operator, token_types.Arithmetic_operator))
                else self.operator.to_string())

    def to_string(self):
        return '{}({})'.format(
            self.to(),
            ', '.join(map(str, self.args)),
        )


class Name_ref(Group_type):
    type_name = 'Name_ref'

    def __init__(self, name):
        self.name = name

    def to_string(self):
        return '{}'.format(
            str(self.name.token),
        )


class Id(Group_type):
    type_name = 'Id'

    def __init__(self, name):
        self.name = name

    def to_string(self):
        return ''.join(
            map(lambda each: ('::' if each == '.' else each),
            map(lambda each: str(each.token), self.name)))


class If(Group_type):
    type_name = 'If'

    def __init__(self, condition, arms):
        self.condition = condition
        self.arms = arms

    def to_string(self):
        return 'if ({})'.format(self.condition)
