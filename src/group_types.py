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
        s = ', '.join(self.functions.keys())
        return '{} with {}'.format(
            str(self.name.token),
            (s or 'no functions'),
        )
