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
        self.main_token = got
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

class Unbalanced_parenthesis(Parser_exception):
    MESSAGE = 'unbalanced parenthesis'

    def __init__(self, where):
        super().__init__(where)

    def message(self):
        return '{}: {}'.format(self.MESSAGE, self.main_token)

class Broken_syntax(Parser_exception):
    MESSAGE = 'broken syntax'

    def __init__(self, got):
        super().__init__(got)

class Tag_enum_without_ctor_call(Parser_exception):
    def __init__(self, where, enum):
        super().__init__(where)
        self.enum_name = enum

    def message(self):
        fmt = '{} is a tag enum, use ctor call to construct its values: {}'
        return fmt.format(self.enum_name, self.main_token)

class Unknown_enum(Parser_exception):
    def __init__(self, where, enum):
        super().__init__(where)
        self.enum_name = enum

    def message(self):
        fmt = '{} is not a known enum: {}'
        return fmt.format(self.enum_name, self.main_token)

class Match_without_with_expressions(Parser_exception):
    MESSAGE = 'match expression without any with expression'

    def __init__(self, where):
        super().__init__(where)

class Mismatched_enums(Parser_exception):
    def __init__(self, where, a, b):
        super().__init__(where)
        self.a = a
        self.b = b

    def message(self):
        return 'match over enum {} includes value of enum {}: {}'.format(
            self.a,
            self.b,
            self.main_token,
        )

class Enum_field_does_not_exist(Parser_exception):
    def __init__(self, where, enum, field):
        super().__init__(where)
        self.enum = enum
        self.field = field

    def message(self):
        return 'enum {} has no field {}: {}'.format(
            self.enum,
            self.field,
            self.main_token,
        )

class Enum_field_not_checked_for(Parser_exception):
    def __init__(self, where, enum, field):
        super().__init__(where)
        self.enum = enum
        self.field = field

    def message(self):
        return 'field {} of enum {} is not checked for: {}'.format(
            self.field,
            self.enum,
            self.main_token,
        )

class Catchall_with_cannot_bind(Parser_exception):
    MESSAGE = 'catch-all with cannot bind'

    def __init__(self, where):
        super().__init__(where)

class Non_tag_field_cannot_bind(Parser_exception):
    def __init__(self, where, enum, field):
        super().__init__(where)
        self.enum = enum
        self.field = field

    def message(self):
        return 'non-tag field {} of enum {} cannot bind: {}'.format(
            self.field,
            self.enum,
            self.main_token,
        )


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


def make_fallout(main_token, message, e):
    return Fallout(
        token = main_token,
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
