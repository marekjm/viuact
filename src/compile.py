#!/usr/bin/env python3

import collections
import json
import os
import re
import sys


import exceptions
import token_types
import group_types
import lowerer


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


def lex(source):
    """Lexing turns a stream of characters into a stream of tokens.
    """
    tokens = []

    def make_token(text, line, character):
        return Token(text, line, character)

    patterns = [
        token_types.Left_paren,     # Punctuation
        token_types.Right_paren,

        token_types.Let,            # Keywords
        token_types.Rec,
        token_types.If,
        token_types.Module,
        token_types.Import,
        token_types.Extern,

        token_types.Struct,         # Basic-type ctors
        token_types.Vector,

        token_types.Ellipsis,

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

        token_types.Actor,          # Keywords

        token_types.Name,           # Names and ids
        token_types.Module_name,

        token_types.Comment,

        token_types.String,         # Literals
        token_types.Float,
        token_types.Timeout,
        token_types.Integer,
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
    literal_types = (token_types.Integer, token_types.String, token_types.Timeout)

    if leader_type is token_types.Let and len(expr) == 3:
        return group_types.Let_binding(
            name = expr[1],
            value = parse_expression(expr[2]),
        )
    elif leader_type is token_types.Let and len(expr) == 4:
        return parse_function(expr)
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
    elif isinstance(leader, (token_types.Logic_operator, token_types.Arithmetic_operator)) and type(expr) is list:
        return group_types.Operator_call(
            operator = expr[0],
            args = [parse_expression(each) for each in expr[1]],
        )
    elif leader_type is token_types.If:
        return group_types.If(
            condition = parse_expression(expr[1]),
            arms = [parse_expression(each) for each in expr[2:]],
        )
    elif leader_type in literal_types:
        return expr
    elif leader_type is token_types.Actor and type(expr[1]) is token_types.Name and type(expr[2]) is list:
        return group_types.Actor_call(
            name = parse_expression(expr[1]),
            args = [parse_expression(each) for each in expr[2]],
        )
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


class Compilation_mode:
    Automatic = 'auto'
    Executable = 'exec'
    Module = 'module'

Valid_compilation_modes = (
    Compilation_mode.Automatic,
    Compilation_mode.Executable,
    Compilation_mode.Module,
)


def print_error(s):
    text = '{}\n'.format(s)
    return sys.stderr.write(text)

HELP = '''{man_executable}(1)

NAME

    {executable} - Viuact compiler

SYNOPSIS

    {executable} <file>
    {exec_blank} --mode (module | exec | auto) <file>
    {exec_blank} --help

DESCRIPTION

    Compiler from Viuact to Viua VM assembly language. Viuact is a
    high-level programming language with a Lisp-like syntax.

OPTIONS

    --help      - display this message
    --mode module | exec | auto
                - set compilation mode; 'auto' is the default one
'''

def print_help(executable_name):
    print(HELP.format(
        man_executable = executable_name.upper(),
        executable = executable_name,
        exec_blank = (' ' * len(executable_name)),
    ).strip())

def main(executable_name, args):
    if '--help' in args:
        print_help(executable_name)
        exit(0)

    if not args or len(args) not in (1, 3):
        print_error('error: invalid number of operands: expected 1 or 3')
        print_error('note: syntax: {} <file>'.format(executable_name))
        print_error('              {} --mode {} <file>'.format(
            executable_name,
            Compilation_mode.Automatic,
        ))
        print_error('              {} --mode {} <file>'.format(
            executable_name,
            Compilation_mode.Executable,
        ))
        print_error('              {} --mode {} <file>'.format(
            executable_name,
            Compilation_mode.Module,
        ))
        exit(1)

    output_directory = './build/_default'
    os.makedirs(output_directory, exist_ok = True)

    compile_as = Compilation_mode.Automatic
    source_file = None
    if len(args) == 1:
        source_file = args[0]
    else:
        if args[0] != '--mode':
            print_error('error: unknown option: {}'.format(repr(args[0])))
            print_error('note: run {} --help to get help'.format(executable_name))
            exit(1)

        compile_as = args[1]
        source_file = args[2]

    if compile_as not in Valid_compilation_modes:
        print_error('error: invalid compilation mode: {}'.format(compile_as))
        exit(1)

    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = strip_comments(lex(source_code))

    groups = group(tokens)
    if not groups:
        sys.stderr.write('error: source file contains no expressions: {}\n'.format(source_file))
        exit(1)

    expressions = parse(groups)

    if compile_as == Compilation_mode.Module:
        module_name = os.path.basename(source_file).split('.')[0]
        module_name = module_name[0].upper() + module_name[1:]
        print('compiling module: {} (from {})'.format(module_name, source_file))

        lowered_function_bodies = []
        try:
            module = group_types.Module(name = token_types.Module_name(module_name))
            for each in expressions:
                if type(each) is group_types.Module:
                    module.module_names.append(str(each.name.token))
                    module.modules[module.module_names[-1]] = each
                elif type(each) is group_types.Function:
                    module.function_names.append(str(each.name.token))
                    module.functions[module.function_names[-1]] = each

            lowered_function_bodies, meta = lowerer.lower_module(
                module_expr = module,
            )
        except (exceptions.Emitter_exception, exceptions.Lowerer_exception,) as e:
            msg, cause = e.args
            line, character = 0, 0

            cause_type = type(cause)
            if cause_type is group_types.Function:
                token = cause.name.token
                line, character = token.location()

            print('{}:{}:{}: {}: {}'.format(
                source_file,
                line + 1,
                character + 1,
                msg,
                cause,
            ))
            raise

        with open(os.path.join(output_directory, '{}.asm'.format(module_name)), 'w') as ofstream:
            ofstream.write('\n\n'.join(lowered_function_bodies))
    elif compile_as == Compilation_mode.Executable:
        module_name = os.path.basename(source_file).split('.')[0]
        print('compiling executable: {} (from {})'.format(module_name, source_file))

        lowered_function_bodies = []
        try:
            lowered_function_bodies, meta = lowerer.lower_file(
                expressions = expressions,
                module_prefix = None,
            )
        except (exceptions.Emitter_exception, exceptions.Lowerer_exception,) as e:
            msg, cause = e.args
            line, character = 0, 0

            cause_type = type(cause)
            if cause_type is group_types.Function:
                token = cause.name.token
                line, character = token.location()

            print('{}:{}:{}: {}: {}'.format(
                source_file,
                line + 1,
                character + 1,
                msg,
                cause,
            ))
            raise

        with open(os.path.join(output_directory, '{}.asm'.format(module_name)), 'w') as ofstream:
            ofstream.write('\n\n'.join(lowered_function_bodies))

main(sys.argv[0], sys.argv[1:])
