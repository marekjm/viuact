#!/usr/bin/env python3

import collections
import json
import re
import sys


import token_types
import group_types


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


def parse_function(source):
    if not isinstance(source[1], token_types.Name):
        raise Exception('expected name, got', source[1])
    if len(source) != 4:
        raise Exception('invalid function definition')

    fn = group_types.Function(name = source[1])

    if not isinstance(source[2], list):
        raise Exception('expected arguments list, got', source[2])
    fn.arguments = source[2]

    if not isinstance(source[3], list):
        raise Exception('expected expression, got', source[3])
    fn.body = source[3]

    return fn

def parse_module(source):
    if not isinstance(source[1], token_types.Name):
        raise Exception('expected name, got', source[1])

    mod = group_types.Module(name = source[1])

    module_contents = source[2]
    for each in module_contents:
        fn = parse_function(each)
        mod.functions[str(fn.name.token)] = fn

    return mod


def parse(groups):
    parsed = []

    for each in groups:
        leader = each[0]
        if isinstance(leader, token_types.Module):
            parsed.append(parse_module(each))
        else:
            raise Exception('invalid leader', leader)

    return parsed


def output_interface_file(expressions):
    is_module = isinstance(expressions[0], group_types.Module)
    if not is_module:
        return

    module_expr = expressions[0]
    module_name = str(module_expr.name.token)

    module_interface = {
        'name': module_name,
        'exports': {},
        'imports': [],
    }

    for fn_name, fn_def in module_expr.functions.items():
        module_interface['exports'][fn_name] = {
            'arity': len(fn_def.arguments),
        }

    print(json.dumps(module_interface, indent=2))

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
        print('\n')

    expressions = parse(groups)
    print(expressions)

    output_interface_file(expressions)

main(sys.argv[1:])
