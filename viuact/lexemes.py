import re


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

class Let(Lexeme):
    pattern = re.compile(r'\blet\b')

class Name(Lexeme):
    pattern = re.compile(r'\b[a-z][a-zA-Z0-9_]*\'?\b')

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
    Let,
    Name,
    Integer,
    String,
]
