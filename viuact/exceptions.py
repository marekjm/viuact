class Viuact_exception(Exception):
    def __init__(self, token):
        self.main_token = token

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


def make_fallout(e_type, message, token):
    e = e_type(message, token)
    return Fallout(
        token = e.main_token,
        message = message,
        cause = e,
    )
