from viuact import token_types


class Viuact_exception(Exception):
    def __init__(self, token):
        self.main_token = token

    def cause(self):
        return self.main_token

    def message(self):
        return self.MESSAGE


class Fallout(Viuact_exception):
    def __init__(self, token, message, cause):
        super().__init__(token)
        self.MESSAGE = message
        self.cause = cause


class Lexer_exception(Viuact_exception):
    pass

class Unexpected_character(Lexer_exception):
    MESSAGE = 'unexpected character'


class Parser_exception(Viuact_exception):
    pass

class Unexpected_token(Parser_exception):
    MESSAGE = 'unexpected token'

    def __init__(self, expected : str, got):
        super().__init__(got)
        self.expected = expected

    def message(self):
        return '{}: {}'.format(self.MESSAGE, self.expected)

class Unexpected_group(Parser_exception):
    MESSAGE = 'unexpected group'

    def __init__(self, expected : str, got):
        super().__init__(got)
        self.expected = expected

    def message(self):
        return '{}: {}'.format(self.MESSAGE, self.expected)


class Emitter_exception(Exception):
    pass

class Source_cannot_be_void(Emitter_exception):
    pass

class Compound_expression_cannot_be_empty(Emitter_exception):
    MESSAGE = 'compound expression cannot be empty'
    pass

class Lowerer_exception(Exception):
    pass

class No_such_function(Lowerer_exception):
    pass

class No_such_module(Exception):
    pass

class Invalid_number_of_arguments(Viuact_exception):
    MESSAGE = 'invalid number of arguments: '

    def __init__(self, base, expected : int, got : int):
        super().__init__(base)
        self.expected = expected
        self.got = got

    def message(self):
        return '{}: expected {}, got {}'.format(self.MESSAGE, self.expected, self.got)

class Invalid_number_of_positional_arguments(Invalid_number_of_arguments):
    MESSAGE = 'invalid number of positional arguments: '

    def message(self):
        return '{}: expected {}, got {}'.format(self.MESSAGE, self.expected, self.got)

class Invalid_number_of_labeled_arguments(Invalid_number_of_arguments):
    MESSAGE = 'invalid number of labeled arguments: '

    def message(self):
        return '{}: expected {}, got {}'.format(self.MESSAGE, self.expected, self.got)


def make_fallout(e):
    return Fallout(
        token = e.main_token,
        message = message,
        cause = e,
    )

def first_usable_token(some_data):
    if isinstance(some_data, token_types.Token_type):
        return some_data

    if type(some_data) is list:
        for each in some_data:
            x = first_usable_token(each)
            if x is not None:
                return x

    return None
