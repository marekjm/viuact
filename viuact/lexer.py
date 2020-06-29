import re

import viuact.util.log
import viuact.errors


class Lexeme:
    patterns = []

    def __init__(self, token):
        self._token = token

    def __str__(self):
        return str(self._token)

    def t(self):
        return type(self)

    def tok(self):
        return self._token

class Left_paren(Lexeme):
    pattern = re.compile('\(')

class Right_paren(Lexeme):
    pattern = re.compile('\)')

class Let(Lexeme):
    pattern = re.compile(r'\blet\b')

class Name(Lexeme):
    pattern = re.compile(r'\b[a-z][a-zA-Z0-9_]*\'?\b')

class String(Lexeme):
    pattern = None

Lexeme.patterns = [
    Left_paren,
    Right_paren,
    Let,
    Name,
    String,
]


class Token:
    def __init__(self, pos, text):
        self._position = pos
        self._text = text

    def __str__(self):
        return self._text

    def at(self):
        return self._position


def lex(text):
    tokens = []

    # Position in analysed text.
    position_line = 0
    position_char = 0
    position_offset = 0

    i = 0
    while i < len(text):
        if text[i] == '\n':
            position_line += 1
            position_char = 0
            position_offset += 1
            i += 1
            continue

        if text[i].strip() == '':
            position_char += 1
            position_offset += 1
            i += 1
            continue

        match_found = False

        if text[i] == '"':
            n = i + 1
            escaped = False
            while n < len(text):
                if text[n] == '"' and not escaped:
                    match_found = True

                    s = text[i:n + 1]

                    position_char = n + 1
                    position_offset = n + 1
                    i = n + 1

                    tokens.append(String(token = Token(
                        pos = (position_line, position_char,),
                        text = s,
                    )))
                    break
                if text[n] == '\\':
                    escaped = not escaped
                if escaped and text[n] != '\\':
                    escaped = False
                n += 1

        if match_found:
            continue

        for lex_t in Lexeme.patterns:
            if lex_t.pattern is None:
                continue
            res = lex_t.pattern.match(text[i:])
            if res is not None:
                s = res.group(0)

                tokens.append(lex_t(token = Token(
                    pos = (position_line, position_char,),
                    text = s,
                )))

                position_char += len(s)
                position_offset += len(s)
                i += len(s)

                match_found = True
                break

        if not match_found:
            raise viuact.errors.Unexpected_character(
                pos = (position_line, position_char,),
                s = text[i],
            )

    return tokens


def to_data(tokens):
    type_to_tag = {}
    for i, each in enumerate(Lexeme.patterns):
        type_to_tag[each] = i

    data = []
    for each in tokens:
        data.append({
            'tag': type_to_tag[each.t()],
            'value': {
                'position': each.tok().at(),
                'text': str(each),
            },
        })

    return { 'tokens': data, }
