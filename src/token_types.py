import re


class Token_type:
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return '{}: {}'.format(self.type_name, self.token)


class Keyword(Token_type):
    def __repr__(self):
        return 'Keyword_{}: {}'.format(self.type_name.lower(), self.token)

class Module(Keyword):
    type_name = 'module'
    pattern = re.compile(r'\bmodule\b')

class Let(Keyword):
    type_name = 'let'
    pattern = re.compile(r'\blet\b')

class Rec(Keyword):
    type_name = 'rec'
    pattern = re.compile(r'\brec\b')

class If(Keyword):
    type_name = 'if'
    pattern = re.compile(r'\bif\b')

class Import(Keyword):
    type_name = 'import'
    pattern = re.compile(r'\bimport\b')

class Struct(Keyword):
    type_name = 'struct'
    pattern = re.compile(r'\bstruct\b')

class Vector(Keyword):
    type_name = 'vector'
    pattern = re.compile(r'\bvector\b')


class Operator(Token_type):
    def __repr__(self):
        return 'Operator_{}: {}'.format(self.type_name.lower(), self.token)

class Or(Operator):
    type_name = 'or'
    pattern = re.compile(r'\bor\b')

class And(Operator):
    type_name = 'and'
    pattern = re.compile(r'\band\b')

class Not(Operator):
    type_name = 'not'
    pattern = re.compile(r'\bnot\b')

class Eq(Operator):
    type_name = 'eq'
    pattern = re.compile(r'=')

class Ne(Operator):
    type_name = 'ne'
    pattern = re.compile(r'!=')

class Lt(Operator):
    type_name = 'lt'
    pattern = re.compile(r'<')

class Lte(Operator):
    type_name = 'lte'
    pattern = re.compile(r'<=')

class Gt(Operator):
    type_name = 'gt'
    pattern = re.compile(r'>')

class Gte(Operator):
    type_name = 'gte'
    pattern = re.compile(r'>=')


class Punctuation(Token_type):
    pass

class Left_paren(Punctuation):
    type_name = 'Left_paren'
    pattern = re.compile('\(')

class Right_paren(Punctuation):
    type_name = 'Right_paren'
    pattern = re.compile('\)')


class Name(Token_type):
    type_name = 'Name'
    pattern = re.compile('[a-zA-Z][a-zA-Z0-9_]*')


class Comment(Token_type):
    type_name = 'Comment'
    pattern = re.compile(';.*\n')


class Literal(Token_type):
    def __repr__(self):
        return 'Literal_{}: {}'.format(self.type_name.lower(), self.token)

class String(Literal):
    type_name = 'string'
    pattern = re.compile('"[^"]*?"')

class Float(Literal):
    type_name = 'float'
    pattern = re.compile('-?(0|[1-9][0-9]*|)\.([0-9]+)')

class Integer(Literal):
    type_name = 'integer'
    pattern = re.compile('(0|-?[1-9][0-9]*)')
