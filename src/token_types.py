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

class Extern(Keyword):
    type_name = 'extern'
    pattern = re.compile(r'\bextern\b')

class Let(Keyword):
    type_name = 'let'
    pattern = re.compile(r'\blet\b')

class Rec(Keyword):
    type_name = 'rec'
    pattern = re.compile(r'\brec\b')

class If(Keyword):
    type_name = 'if'
    pattern = re.compile(r'\bif\b')

class Ctor_keyword(Keyword):
    pass

class Import(Ctor_keyword):
    type_name = 'import'
    pattern = re.compile(r'\bimport\b')

class Struct(Ctor_keyword):
    type_name = 'struct'
    pattern = re.compile(r'\bstruct\b')

class Vector(Ctor_keyword):
    type_name = 'vector'
    pattern = re.compile(r'\bvector\b')

class Actor(Keyword):
    type_name = 'actor'
    pattern = re.compile(r'\bactor\b')


class Operator(Token_type):
    def __repr__(self):
        return 'Operator_{}: {}'.format(self.type_name.lower(), self.token)

class Logic_operator(Operator):
    pass

class Arithmetic_operator(Operator):
    pass

class Or(Logic_operator):
    type_name = 'or'
    pattern = re.compile(r'\bor\b')

class And(Logic_operator):
    type_name = 'and'
    pattern = re.compile(r'\band\b')

class Not(Logic_operator):
    type_name = 'not'
    pattern = re.compile(r'\bnot\b')

class Eq(Logic_operator):
    type_name = 'eq'
    pattern = re.compile(r'=')

class Ne(Logic_operator):
    type_name = 'ne'
    pattern = re.compile(r'!=')

class Lt(Logic_operator):
    type_name = 'lt'
    pattern = re.compile(r'<')

class Lte(Logic_operator):
    type_name = 'lte'
    pattern = re.compile(r'<=')

class Gt(Logic_operator):
    type_name = 'gt'
    pattern = re.compile(r'>')

class Gte(Logic_operator):
    type_name = 'gte'
    pattern = re.compile(r'>=')

class Add(Arithmetic_operator):
    type_name = 'add'
    pattern = re.compile(r'\+')

class Subtract(Arithmetic_operator):
    type_name = 'subtract'
    pattern = re.compile(r'-')

class Mul(Arithmetic_operator):
    type_name = 'mul'
    pattern = re.compile(r'\*')

class Div(Arithmetic_operator):
    type_name = 'div'
    pattern = re.compile(r'/')

class Dot(Operator):
    type_name = 'dot'
    pattern = re.compile(r'\.')


class Ellipsis(Operator):
    type_name = 'ellipsis'
    pattern = re.compile(r'\.\.\.')


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
    pattern = re.compile('([a-z][a-zA-Z0-9_]*|_)')

class Module_name(Token_type):
    type_name = 'Module_name'
    pattern = re.compile('[A-Z][a-zA-Z0-9_]*')


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
