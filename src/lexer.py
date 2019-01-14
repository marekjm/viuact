import re


import token_types


class Token:
    def __init__(self, text, line, character):
        self._text = text
        self.line = line
        self.character = character

    def __str__(self):
        return self._text

    def __repr__(self):
        return repr(self._text)

    def __eq__(self, other):
        return self._text == str(other)

    def __len__(self):
        return len(self._text)

    def location(self):
        return (self.line, self.character,)

    @staticmethod
    def to_data(self):
        return {
            'text': self._text,
            'line': self.line,
            'char': self.character,
        }

    @staticmethod
    def from_data(data):
        return Token(
            text = data['text'],
            line = data['line'],
            character = data['char'],
        )

def lex(source):
    """Lexing turns a stream of characters into a stream of tokens.
    """
    tokens = []

    def make_token(text, line, character):
        return Token(text, line, character)

    patterns = [
        token_types.Left_paren,     # Punctuation
        token_types.Right_paren,
        token_types.Left_curly,
        token_types.Right_curly,

        token_types.Let,            # Keywords
        token_types.Rec,
        token_types.If,
        token_types.Module,
        token_types.Import,
        token_types.Extern,

        token_types.Struct,         # Basic-type ctors
        token_types.Vector,

        token_types.Ellipsis,

        token_types.String,         # Literals
        token_types.Timeout,
        token_types.Integer,
        token_types.Float,
        token_types.Boolean,

        token_types.Or,             # Operators
        token_types.And,
        token_types.Not,
        token_types.Eq,
        token_types.Ne,
        token_types.Lt,
        token_types.Lte,
        token_types.Gt,
        token_types.Gte,
        token_types.Add,
        token_types.Subtract,
        token_types.Mul,
        token_types.Div,
        token_types.Dot,
        token_types.Field_assignment,

        token_types.Actor,          # Call keywords
        token_types.Tailcall,
        token_types.Defer,
        token_types.Try,
        token_types.Catch,
        token_types.In,

        token_types.Name,           # Names and ids
        token_types.Module_name,

        token_types.Comment,
    ]

    i = 0
    line = 0
    character_in_line = 0
    while i < len(source):
        match_found = False
        for each in patterns:
            r = re.match(each.pattern, source[i:])
            if r is not None:
                match_found = True
                s = r.group(0)
                tokens.append(each(make_token(
                    text = s,
                    line = line,
                    character = character_in_line,
                )))
                i += len(s)
                character_in_line += len(s)
                break

        if match_found:
            continue

        if source[i] == '\n':
            i += 1
            character_in_line = 0
            line += 1
            continue

        if source[i].strip() == '':
            i += 1
            character_in_line += 1
            continue

        raise Exception('unexpected token', repr(source[i]))

    return tokens

def to_data(lexeme):
    return {
        'token': Token.to_data(lexeme.token),
        'type': lexeme.type_name,
    }

def strip_comments(tokens):
    return list(filter(lambda each: (not isinstance(each, token_types.Comment)), tokens))
