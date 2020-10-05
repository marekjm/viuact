import re


class Token:
    def __init__(self, pos, text):
        self._position = pos
        self._text = text

    def __str__(self):
        return self._text

    def at(self):
        return self._position


class Lexeme:
    patterns = []

    def __init__(self, token):
        if type(token) is not Token:
            raise TypeError(
                'token is not of type \'viuact.lexemes.Token\': {}'.format(
                    str(type(token))[8:-2],))
        self._token = token

    def __str__(self):
        return str(self._token)

    def t(self):
        return type(self)

    def tok(self):
        return self._token

class Comment(Lexeme):
    pattern = None

class Left_paren(Lexeme):
    pattern = re.compile('\(')

class Right_paren(Lexeme):
    pattern = re.compile('\)')

class Left_curly(Lexeme):
    pattern = re.compile('\{')

class Right_curly(Lexeme):
    pattern = re.compile('\}')

class Path_resolution(Lexeme):
    pattern = re.compile('::')

class Arrow_right(Lexeme):
    pattern = re.compile(r'->')

class Operator_dot(Lexeme):
    pattern = re.compile(r'\.')

class Operator_concat(Lexeme): # or double-dot? See "double dotted note" in musical notation.
    pattern = re.compile(r'\.\.')

class Operator_ellipsis(Lexeme):
    pattern = re.compile(r'\.\.\.')

class Operator_plus(Lexeme):
    pattern = re.compile(r'\+')

class Operator_minus(Lexeme):
    pattern = re.compile(r'\-')

class Operator_star(Lexeme):
    pattern = re.compile(r'\*')

class Operator_solidus(Lexeme):
    pattern = re.compile(r'/')

class Operator_lte(Lexeme):
    pattern = re.compile(r'<=')

class Operator_lt(Lexeme):
    pattern = re.compile(r'<')

class Operator_gte(Lexeme):
    pattern = re.compile(r'>=')

class Operator_gt(Lexeme):
    pattern = re.compile(r'>')

class Operator_neq(Lexeme):
    pattern = re.compile(r'!=')

class Operator_eq(Lexeme):
    pattern = re.compile(r'=')

class Let(Lexeme):
    pattern = re.compile(r'\blet\b')

class Val(Lexeme):
    pattern = re.compile(r'\bval\b')

class If(Lexeme):
    pattern = re.compile(r'\bif\b')

class Enum(Lexeme):
    pattern = re.compile(r'\benum\b')

class Match(Lexeme):
    pattern = re.compile(r'\bmatch\b')

class With(Lexeme):
    pattern = re.compile(r'\bwith\b')

class Exception_def(Lexeme):
    pattern = re.compile(r'\bexception\b')

class Throw(Lexeme):
    pattern = re.compile(r'\bthrow\b')

class Try(Lexeme):
    pattern = re.compile(r'\btry\b')

class Catch(Lexeme):
    pattern = re.compile(r'\bcatch\b')

class Type(Lexeme):
    pattern = re.compile(r'\btype\b')

class Struct(Lexeme):
    pattern = re.compile(r'\bstruct\b')

class Of(Lexeme):
    pattern = re.compile(r'\bof\b')

class Tail(Lexeme):
    pattern = re.compile(r'\btailcall\b')

class Drop(Lexeme):
    pattern = re.compile(r'\b_\b')

class Bool_literal(Lexeme):
    pattern = re.compile(r'\b(true|false)\b')

class Name(Lexeme):
    pattern = re.compile(r'\b[a-z][a-zA-Z0-9_]*\'?')

class Labelled_name(Lexeme):
    pattern = re.compile(r'~[a-z][a-zA-Z0-9_]*\'?')

class Template_parameter(Lexeme):
    pattern = re.compile(r'\'[a-z][a-zA-Z0-9_]*\b')

class Mod_name(Lexeme):
    pattern = re.compile(r'[A-Z][a-zA-Z0-9_]*\b')

class Enum_ctor_name(Lexeme):
    pattern = re.compile(r'[A-Z][a-zA-Z0-9_]*\b')

class Integer(Lexeme):
    pattern = re.compile(r'-?\b(0|[1-9][0-9]*|0x[a-f0-9]+|0o[0-7]+|0b[01]+)\b')

class String(Lexeme):
    pattern = None

Lexeme.patterns = [
    Comment,
    Left_paren,
    Right_paren,
    Left_curly,
    Right_curly,
    Path_resolution,
    Arrow_right,
    Operator_ellipsis,
    Operator_concat,
    Operator_dot,
    Operator_plus,
    Operator_minus,
    Operator_star,
    Operator_solidus,
    Operator_lte,
    Operator_lt,
    Operator_gte,
    Operator_gt,
    Operator_neq,
    Operator_eq,
    Let,
    Val,
    If,
    Enum,
    Match,
    With,
    Exception_def,
    Throw,
    Try,
    Catch,
    Type,
    Struct,
    Of,
    Bool_literal,
    Labelled_name,
    Template_parameter,
    Mod_name,
    Name,
    Drop,
    Integer,
    String,
]


class Phantom(Lexeme):
    pass

class Paren_tag(Phantom):
    pass

class Curly_tag(Phantom):
    pass

class Exception_name(Phantom):
    pass

class Record_ctor_field(Phantom):
    pass
