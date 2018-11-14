#!/usr/bin/env python3

import collections
import json
import re
import sys


import token_types
import group_types
import lowerer


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
    """Lexing turns a stream of characters into a stream of tokens.
    """
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
        token_types.Dot,

        token_types.Name,           # Names and ids
        token_types.Module_name,

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
            continue

        if isinstance(each, token_types.Dot):
            name_types = (token_types.Module_name, token_types.Name,)
            if not ((type(grouped[-1]) in name_types) or
                (type(grouped[-1]) is list and type(grouped[-1][-1]) in name_types)):
                raise Exception(
                    'operator dot must follow module name or name, got',
                    grouped[-1],
                    grouped[-1][-1],
                )
            if type(tokens[i+1]) not in (token_types.Module_name, token_types.Name):
                raise Exception('expected module name or name to follow operator dot, got', tokens[i+1])

            if type(grouped[-1]) is list:
                grouped[-1].extend([each, tokens[i+1],])
            else:
                grouped[-1] = [grouped[-1], each, tokens[i+1],]
            i += 2
            continue

        grouped.append(each)
        i += 1

        if isinstance(each, token_types.Right_paren):
            return grouped, i

    return grouped, i

def group(tokens):
    """Grouping turns a stream of tokens into a stream of groups representing
    nested expressions surrounded by ().
    """
    groups = []

    i = 0
    while i < len(tokens):
        each = tokens[i]
        g, n = group_impl(tokens[i:])
        groups.append(g[1:-1])
        i += n

    return groups


def parse_expression(expr):
    """Parsing turns "anonymous" groups of tokens into syntactic entities.
    Let bindings, name references, function calls, etc.
    """
    leader = (expr[0] if type(expr) is list else expr)
    leader_type = type(leader)

    name_types = (token_types.Module_name, token_types.Name,)
    literal_types = (token_types.Integer, token_types.String,)

    if leader_type is token_types.Let:
        return group_types.Let_binding(
            name = expr[1],
            value = parse_expression(expr[2]),
        )
    elif leader_type is token_types.Name and type(expr) is list:
        return group_types.Function_call(
            name = expr[0],
            args = [parse_expression(each) for each in expr[1]],
        )
    elif leader_type is list and type(leader[0]) in name_types:
        return group_types.Function_call(
            name = parse_expression(expr[0]),
            args = [parse_expression(each) for each in expr[1]],
        )
    elif leader_type in name_types and type(expr) is list and type(expr[1]) is token_types.Dot:
        return group_types.Id(
            name = expr,
        )
    elif leader_type is token_types.Name:
        return group_types.Name_ref(
            name = expr,
        )
    elif leader_type in literal_types:
        return expr
    else:
        raise Exception('invalid expression in function body', expr)

def parse_function_body(source):
    body = []

    for each in source:
        body.append(parse_expression(each))

    return body

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
    fn.body = parse_function_body(source[3])

    return fn

def parse_module(source):
    if not isinstance(source[1], token_types.Module_name):
        raise Exception('expected module name, got', source[1])

    mod = group_types.Module(name = source[1])

    module_contents = source[2]
    for each in module_contents:
        if type(each[0]) is token_types.Let:
            fn = parse_function(each)
            mod.function_names.append(str(fn.name.token))
            mod.functions[mod.function_names[-1]] = fn
        elif type(each[0]) is token_types.Module:
            md = parse_module(each)
            mod.module_names.append(str(md.name.token))
            mod.modules[mod.module_names[-1]] = md
        else:
            raise Exception('expected `module` or `let` keyword, got', each[0])

    return mod


def parse(groups):
    parsed = []

    for each in groups:
        leader = each[0]
        if isinstance(leader, token_types.Module):
            parsed.append(parse_module(each))
        elif isinstance(leader, token_types.Let):
            parsed.append(parse_function(each))
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

    # FIXME save the interface to file
    for fn_name, fn_def in module_expr.functions.items():
        module_interface['exports'][fn_name] = {
            'arity': len(fn_def.arguments),
        }


def main(args):
    source_file = args[0]
    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = strip_comments(lex(source_code))

    groups = group(tokens)

    expressions = parse(groups)

    output_interface_file(expressions)

    lowered_function_bodies = lowerer.lower_file(expressions)

    if len(args) > 1:
        with open(args[1], 'w') as ofstream:
            ofstream.write('\n\n'.join(lowered_function_bodies))

main(sys.argv[1:])
