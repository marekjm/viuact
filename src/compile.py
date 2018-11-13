#!/usr/bin/env python3

import collections
import json
import re
import sys


import token_types
import group_types
import emitter


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

            # print('gi', grouped)
            continue

        if isinstance(each, token_types.Dot):
            name_types = (token_types.Module_name, token_types.Name,)
            if ((type(grouped[-1]) not in name_types) or
                (type(grouped[-1]) is list and type(grouped[-1][-1]) not in name_types)):
                raise Exception('operator dot must follow module name or name, got', grouped[-1])
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
        # print('g', g, groups)

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
        fn = parse_function(each)
        mod.functions[str(fn.name.token)] = fn

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


def lower_function_body(body):
    instructions = [
        body[0].to_string(),   # signature
    ]

    for each in body[1:-1]:
        instructions.append('    {}'.format(
            each.to_string(),
        ))

    instructions.append(body[-1].to_string())  # .end

    return '\n'.join(instructions)


def output_function_body(fn):
    body = [
        emitter.Verbatim('.function: {}/{}'.format(
            str(fn.name.token),
            len(fn.arguments),
        )),
    ]

    inner_body = []
    state = emitter.State()

    for i, each in enumerate(fn.arguments):
        source = emitter.Slot(
            None,
            i,
            'parameters',
        )
        dest = state.get_slot(
            str(each.token),
        )
        inner_body.append(emitter.Move.make_move(
            source,
            dest,
        ))
    if fn.arguments:
        inner_body.append(emitter.Verbatim(''))

    for each in fn.body:
        # Expressions evaluated at function-level are given anonymous
        # slots.
        # Why? Because they are not assigned to anything. If an
        # expression is assigned to an anonymous slot it can decide for
        # itself what to do with this situation; function calls will
        # return to void, literals and let-bindings will be created.
        emitter.emit_expr(
            body = inner_body,
            expr = each,
            state = state,
        )
        inner_body.append(emitter.Verbatim(''))

    print(state.name_to_slot)

    body.append(emitter.Verbatim('allocate_registers %{} local'.format(
        state.next_slot[emitter.LOCAL_REGISTER_SET],
    )))
    body.append(emitter.Verbatim(''))
    body.extend(inner_body)
    body.append(emitter.Move.make_move(
        state.last_used_slot,
        emitter.Slot(None, 0,)
    ))
    body.append(emitter.Verbatim('return'))
    body.append(emitter.Verbatim('.end'))
    return body

def main(args):
    source_file = args[0]
    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = strip_comments(lex(source_code))

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

    output_interface_file(expressions)

    is_module = isinstance(expressions[0], group_types.Module)
    if not is_module:
        return

    lowered_function_bodies = []

    for each in expressions:
        print(type(each))
        if type(each) is group_types.Module:
            module_expr = expressions[0]
            for fn_name, fn_def in module_expr.functions.items():
                print('   ', fn_name, fn_def, type(fn_def))
                print('   ', fn_def.body)
                body = output_function_body(fn_def)
                print('   ', body)
                s = lower_function_body(body)
                print(s)
                lowered_function_bodies.append(s)
        elif type(each) is group_types.Function:
            body = output_function_body(each)
            s = lower_function_body(body)
            lowered_function_bodies.append(s)

    if len(args) > 1:
        with open(args[1], 'w') as ofstream:
            ofstream.write('\n\n'.join(lowered_function_bodies))

main(sys.argv[1:])
