class Form:
    pass


class Fn(Form):
    def __init__(self, name, parameters, expression):
        self._name = name               # lexeme
        self._parameters = parameters   # [form]
        self._expression = expression   # form

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
