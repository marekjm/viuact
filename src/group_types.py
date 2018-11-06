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

    def to_string(self):
        return '{}({})'.format(
            str(self.name.token),
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
