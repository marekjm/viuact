import re


from viuact import exceptions, token_types


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
        token_types.Const,
        token_types.Rec,
        token_types.Val,
        token_types.If,
        token_types.Module,
        token_types.Import,
        token_types.Extern,
        token_types.Case,
        token_types.Of,
        token_types.Class,
        token_types.In,
        token_types.Match,
        token_types.With,
        token_types.Trait,
        token_types.Impl,
        token_types.For,

        token_types.Struct,         # Basic-type ctors
        token_types.Vector,

        token_types.Enum,           # ViuAct types; these are compiled away
                                    # during the lowering stage.

        token_types.Ellipsis,

        token_types.Timeout,        # Literals
        token_types.Float,
        token_types.Integer,
        token_types.Boolean,

        token_types.Or,             # Operators
        token_types.And,
        token_types.Not,
        token_types.Eq,
        token_types.Ne,
        token_types.Lte,
        token_types.Lt,
        token_types.Gte,
        token_types.Gt,
        token_types.Add,
        token_types.Subtract,
        token_types.Mul,
        token_types.Div,
        token_types.Pointer_dereference,
        token_types.Dot,
        token_types.Field_assignment,

        token_types.Actor,          # Call keywords
        token_types.Tailcall,
        token_types.Defer,
        token_types.Watchdog,

        token_types.Try,            # Exception handling
        token_types.Catch,
        token_types.Throw,

        token_types.Labeled_parameter_name,  # Names and ids
        token_types.Template_parameter_name,
        token_types.Name,
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

        if source[i] == '"':
            n = i + 1
            escaped = False
            while n < len(source):
                if source[n] == '"' and not escaped:
                    match_found = True
                    s = source[i:n + 1]
                    i = n + 1
                    tokens.append(token_types.String(make_token(
                        text = s,
                        line = line,
                        character = character_in_line,
                    )))
                    character_in_line += len(s)
                    break
                if source[n] == '\\':
                    escaped = not escaped
                if escaped and source[n] != '\\':
                    escaped = False
                n += 1

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

        raise exceptions.Unexpected_character(make_token(
            text = source[i],
            line = line,
            character = character_in_line,
        ))

    return tokens

def to_data(lexeme):
    return {
        'token': Token.to_data(lexeme.token),
        'type': lexeme.type_name,
    }

def strip_comments(tokens):
    return list(filter(lambda each: (not isinstance(each, token_types.Comment)), tokens))
