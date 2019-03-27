import re


class Token_type:
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return '{}: {}'.format(self.type_name, self.token)

    def to_data(self):
        return {
            'token': self.token.to_data(self.token),
            'type': self.type_name,
        }


class Keyword(Token_type):
    def __repr__(self):
        return 'Keyword_{}: {}'.format(self.type_name.lower(), self.token)

class Module(Token_type):
    type_name = 'Keyword_module'
    pattern = re.compile(r'\bmodule\b')

class Extern(Token_type):
    type_name = 'Keyword_extern'
    pattern = re.compile(r'\bextern\b')

class Let(Token_type):
    type_name = 'Keyword_let'
    pattern = re.compile(r'\blet\b')

class Rec(Token_type):
    type_name = 'Keyword_rec'
    pattern = re.compile(r'\brec\b')

class If(Token_type):
    type_name = 'Keyword_if'
    pattern = re.compile(r'\bif\b')

class Import(Token_type):
    type_name = 'Keyword_import'
    pattern = re.compile(r'\bimport\b')

class Struct(Token_type):
    type_name = 'Keyword_struct'
    pattern = re.compile(r'\bstruct\b')

class Vector(Token_type):
    type_name = 'Keyword_vector'
    pattern = re.compile(r'\bvector\b')

class Actor(Token_type):
    type_name = 'Keyword_actor'
    pattern = re.compile(r'\bactor\b')

class Tailcall(Token_type):
    type_name = 'keyword_tailcall'
    pattern = re.compile(r'\btailcall\b')

class Defer(Token_type):
    type_name = 'keyword_defer'
    pattern = re.compile(r'\bdefer\b')

class Watchdog(Token_type):
    type_name = 'keyword_watchdog'
    pattern = re.compile(r'\bwatchdog\b')

class Of(Token_type):
    type_name = 'Keyword_of'
    pattern = re.compile(r'\bof\b')

class With(Token_type):
    type_name = 'Keyword_with'
    pattern = re.compile(r'\bwith\b')

class Try(Token_type):
    type_name = 'keyword_try'
    pattern = re.compile(r'\btry\b')

class Catch(Token_type):
    type_name = 'keyword_catch'
    pattern = re.compile(r'\bcatch\b')

class In(Token_type):
    type_name = 'keyword_in'
    pattern = re.compile(r'\bin\b')

class Or(Token_type):
    type_name = 'Operator_or'
    pattern = re.compile(r'\bor\b')

class And(Token_type):
    type_name = 'Operator_and'
    pattern = re.compile(r'\band\b')

class Not(Token_type):
    type_name = 'Operator_not'
    pattern = re.compile(r'\bnot\b')

class Eq(Token_type):
    type_name = 'Operator_eq'
    pattern = re.compile(r'=')

class Ne(Token_type):
    type_name = 'Operator_ne'
    pattern = re.compile(r'!=')

class Lt(Token_type):
    type_name = 'Operator_lt'
    pattern = re.compile(r'<')

class Lte(Token_type):
    type_name = 'Operator_lte'
    pattern = re.compile(r'<=')

class Gt(Token_type):
    type_name = 'Operator_gt'
    pattern = re.compile(r'>')

class Gte(Token_type):
    type_name = 'Operator_gte'
    pattern = re.compile(r'>=')

class Add(Token_type):
    type_name = 'Operator_add'
    pattern = re.compile(r'\+')

class Subtract(Token_type):
    type_name = 'Operator_subtract'
    pattern = re.compile(r'-')

class Mul(Token_type):
    type_name = 'Operator_mul'
    pattern = re.compile(r'\*')

class Div(Token_type):
    type_name = 'Operator_div'
    pattern = re.compile(r'/')

class Pointer_dereference(Token_type):
    type_name = 'Operator_pointer_dereference'
    pattern = re.compile(r'\^')

class Dot(Token_type):
    type_name = 'Operator_dot'
    pattern = re.compile(r'\.')

class Field_assignment(Token_type):
    type_name = 'Operator_field_assignment'
    pattern = re.compile(r':=')

class Ellipsis(Token_type):
    type_name = 'Operator_ellipsis'
    pattern = re.compile(r'\.\.\.')

class Left_paren(Token_type):
    type_name = 'Left_paren'
    pattern = re.compile('\(')

class Right_paren(Token_type):
    type_name = 'Right_paren'
    pattern = re.compile('\)')

class Left_curly(Token_type):
    type_name = 'Left_curly'
    pattern = re.compile('\{')

class Right_curly(Token_type):
    type_name = 'Right_curly'
    pattern = re.compile('\}')

class Name(Token_type):
    type_name = 'Name'
    pattern = re.compile('([a-z][a-zA-Z0-9_]*|_)')

class Module_name(Token_type):
    type_name = 'Module_name'
    pattern = re.compile('[A-Z][a-zA-Z0-9_]*')

class Exception_tag_name(Token_type):
    type_name = 'Exception_tag_name'
    pattern = None

class Comment(Token_type):
    type_name = 'Comment'
    pattern = re.compile(';.*')

class String(Token_type):
    type_name = 'Literal_string'
    pattern = re.compile('"[^"]*?"')

class Float(Token_type):
    type_name = 'Literal_float'
    pattern = re.compile('-?(0|[1-9][0-9]*|)\.([0-9]+)')

class Integer(Token_type):
    type_name = 'Literal_integer'
    pattern = re.compile('(0|-?[1-9][0-9]*)')

class Timeout(Token_type):
    type_name = 'Literal_timeout'
    pattern = re.compile('((0|[1-9][0-9]*)m?s|infinity)')

class Boolean(Token_type):
    type_name = 'Literal_boolean'
    pattern = re.compile(r'\b(true|false)\b')

class Compound_expression_marker(Token_type):
    type_name = 'Internal_compound_expression_marker'
    pattern = None


OPERATOR_TYPES = (
    Or,
    And,
    Not,
    Eq,
    Ne,
    Lt,
    Lte,
    Gt,
    Gte,
    Add,
    Subtract,
    Mul,
    Div,
)
