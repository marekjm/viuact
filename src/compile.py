#!/usr/bin/env python3

import json
import re
import sys


import token_types


def group_impl(tokens):
    grouped = [tokens[0]]

    i = 1
    while i < len(tokens):
        each = tokens[i]

        if isinstance(each, token_types.Left_paren):
            g, n = group_impl(tokens[i:])
            grouped.append(g[1:-1])
            i += n

            # print('gi', grouped)
            continue

        grouped.append(each)
        i += 1

        if isinstance(each, token_types.Right_paren):
            return grouped, i

    return grouped, i

def group(tokens):
    groups = []

    i = 0
    while i < len(tokens):
        each = tokens[i]

        g, n = group_impl(tokens[i:])
        # print('g', g, groups)

        groups.append(g[1:-1])
        i += n

    return groups


class Token:
    def __init__(self, text):
        self._text = text

    def __str__(self):
        return self._text

    def __repr__(self):
        return repr(self._text)

    def __eq__(self, other):
        return self._text == str(other)

    def __len__(self):
        return len(self._text)


def lex(source):
    tokens = []

    def make_token(text):
        return Token(text)

    patterns = [
        token_types.Left_paren,     # Punctuation
        token_types.Right_paren,

        token_types.Let,            # Keywords
        token_types.Rec,
        token_types.If,
        token_types.Module,
        token_types.Import,

        token_types.Struct,         # Basic-type ctors
        token_types.Vector,

        token_types.Or,             # Operators
        token_types.And,
        token_types.Not,
        token_types.Eq,
        token_types.Ne,
        token_types.Lt,
        token_types.Lte,
        token_types.Gt,
        token_types.Gte,

        token_types.Name,           # Names and ids

        token_types.Comment,

        token_types.String,         # Literals
        token_types.Float,
        token_types.Integer,
    ]
    # pats = [
    #     re.compile('->'),
    #     re.compile('\*'),
    #     re.compile('/'),
    #     re.compile('\+'),
    #     re.compile('-'),
    # ]

    i = 0
    while i < len(source):
        match_found = False
        for each in patterns:
            r = re.match(each.pattern, source[i:])
            if r is not None:
                match_found = True
                s = r.group(0)
                tokens.append(each(make_token(s)))
                i += len(s)
                break

        if match_found:
            continue

        if source[i].strip() == '':
            i += 1
            continue

        raise Exception('unexpected token', repr(source[i]))

    return tokens


def strip_comments(tokens):
    return list(filter(lambda each: (not isinstance(each, token_types.Comment)), tokens))

def main(args):
    source_file = args[0]
    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = strip_comments(lex(source_code))
    # [print(each) for each in tokens]

    groups = group(tokens)
    if True:
        def encode_groups(obj):
            if isinstance(obj, Token):
                return str(obj)
            if isinstance(obj, token_types.Token_type):
                return repr(obj)
            raise TypeError(f'Object of type {obj.__class__.__name__} '
                            f'is not JSON serializable')
        print(json.dumps(groups, indent=2, default=encode_groups))

main(sys.argv[1:])
