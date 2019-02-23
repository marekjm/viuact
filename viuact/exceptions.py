class Viuact_exception(Exception):
    def message(self):
        return self.MESSAGE


class Lexer_exception(Viuact_exception):
    pass

class Unexpected_character(Lexer_exception):
    MESSAGE = 'unexpected character'


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
