import viuact.util.log
import viuact.errors
import viuact.lexemes
import viuact.sl


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

        if text[i:].startswith('(*'):
            balance = 1
            n = (i + 2)

            while balance:
                if text[n:].startswith('(*'):
                    balance += 1
                    n += 2
                elif text[n:].startswith('*)'):
                    balance -= 1
                    n += 2
                else:
                    n += 1

            s = text[i:n]
            tokens.append(viuact.lexemes.Comment(token = viuact.lexemes.Token(
                pos = (position_line, position_char,),
                text = s,
            )))

            position_line += s.count('\n')
            position_char = (len(s) - s.rfind('\n') - 1)
            position_offset = n
            i = n

            continue

        if text[i] == ';':
            n = text.find('\n', i + 1)

            s = text[i:n]

            tokens.append(viuact.lexemes.Comment(token = viuact.lexemes.Token(
                pos = (position_line, position_char,),
                text = s,
            )))

            position_line += 1
            position_char = 0
            position_offset = n + 1
            i = n + 1

            continue

        match_found = False

        if text[i] == '"':
            n = i + 1
            escaped = False
            while n < len(text):
                if text[n] == '"' and not escaped:
                    match_found = True

                    s = text[i:n + 1]

                    tokens.append(viuact.lexemes.String(
                        token = viuact.lexemes.Token(
                            pos = (position_line, position_char,),
                            text = s,
                    )))

                    position_char = n + 1
                    position_offset = n + 1
                    i = n + 1

                    break
                if text[n] == '\\':
                    escaped = not escaped
                if escaped and text[n] != '\\':
                    escaped = False
                n += 1

        if match_found:
            continue

        for lex_t in viuact.lexemes.Lexeme.patterns:
            if lex_t.pattern is None:
                continue
            res = lex_t.pattern.match(text[i:])
            if res is not None:
                s = res.group(0)

                tokens.append(lex_t(token = viuact.lexemes.Token(
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
    for i, each in enumerate(viuact.lexemes.Lexeme.patterns):
        type_to_tag[each] = i

    data = []
    for each in tokens:
        data.append(viuact.sl.data_of_lexeme(each, type_to_tag))

    return { 'tokens': data, }
