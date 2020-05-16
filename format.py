#!/usr/bin/env python3

import os
import sys

import viuact
from viuact import token_types, group_types, lexer, parser
import viuact.util.help


HELP = '''{NAME}
    {executable} - format Viuact source code

{SYNOPSIS}
    {exec_tool} [-i] [-s %a(n)] %arg(file).vt
    {exec_blank} --version
    {exec_blank} --help

{DESCRIPTION}
    %text
    Format Viuact source code according to a predefined coding style. This helps
    enforcing a uniform look for all source code.

{OPTIONS}
    %opt(-i)
        Edit the file in-place instead of printing formatted source code on
        standard output.

    %opt(-s) %arg(n)
        %text
        Use %fg(arg)n%r spaces as indent level. The default value is
        %fg(int)4%r.

    %opt(--version)
        Display version information.

    %opt(--help)
        Display this help screen.

{COPYRIGHT}
    %copyright(2019-2020) Marek Marecki

    %text
    Some parts of the code were developed at Polish-Japanse Academy Of
    Information Technology in Gdańsk, Poland.

    This is Free Software published under GNU GPL v3 license.
'''


EXECUTABLE = 'viuact-format'


class Formatter_error(Exception):
    def __init__(self, what):
        self.what = what

    def __str__(self):
        dafuq = self.what
        if type(dafuq) == list:
            dafuq = dafuq[0]
        try:
            line, character = dafuq.token.location()
            return 'unexpected token: {}:{} = {}'.format(
                line + 1,
                character + 1,
                self.what,
            )
        except Exception:
            fmt = 'unexpected token: (failed to extract location from {}: {})'
            return fmt.format(type(dafuq), dafuq)

class Unexpected_token(Formatter_error):
    pass

class Bad_formal_parameter(Formatter_error):
    pass

class Bad_expression(Formatter_error):
    pass


#
# Formatting functions.
#

def deeper_indent(indent):
    return (indent[0], indent[1] + 1,)

def shallower_indent(indent):
    return (indent[0], max(0, indent[1] - 1),)

def make_indent(indent):
    return (' ' * (indent[0] * indent[1]))

def format_enum(what, indent):
    formatted = '{}(enum {} (\n'.format(
        make_indent(indent),
        what[1].token,
    )

    for each in what[2]:
        s = None
        if type(each) == token_types.Module_name:
            s = '{}'.format(
                each.token,
            )
        elif type(each) == list:
            s = '({} {})'.format(
                each[0].token,
                each[1].token,
            )
        else:
            raise Bad_expression(each)

        formatted += '{}{}\n'.format(
            make_indent(deeper_indent(indent)),
            s,
        )

    formatted += '{}))'.format(make_indent(indent))
    return formatted

def format_formal_parameters(what, indent):
    formatted = []

    for each in what:
        if type(each) == token_types.Name:
            formatted.append(str(each.token))
        elif type(each) == token_types.Labeled_parameter_name:
            formatted.append(str(each.token))
        elif type(each) == list:
            s = '({} {})'.format(
                each[0].token,
                format_expression(each[1], indent),
            )
            formatted.append(s)
        else:
            raise Bad_formal_parameter(each)

    return '({})'.format(' '.join(formatted))

def flatten_dot_path(what):
    flattened = []
    while what:
        if type(what) in (token_types.Module_name, token_types.Name,):
            flattened.append(what)
            break
        _, what, leaf = what
        flattened.append(leaf)
    flattened.reverse()
    return flattened

def format_dot_path(what):
    return '.'.join(map(lambda each: str(each.token), flatten_dot_path(what)))

def format_with(what, indent):
    formatted = '{}(with {}'.format(
        make_indent(indent),
        format_expression(what[1], indent = indent),
    )

    expr = what[2]
    if len(what) == 4:
        formatted += ' {}'.format(
            format_expression(what[2], indent = indent),
        )
        expr = what[3]

    if type(expr) == list and type(expr[0]) == token_types.Compound_expression_marker:
        formatted += ' '
    else:
        formatted += '\n{}'.format(make_indent(deeper_indent(indent)))

    formatted += '{})'.format(format_expression(expr, indent = indent))

    return formatted

def format_match(what, indent):
    formatted = '(match {} (\n'.format(
        format_expression(what[1], indent),
    )
    exprs = []
    for each in what[2]:
        exprs.append(format_with(each, indent = deeper_indent(indent)))
    formatted += '\n'.join(exprs)
    formatted += '\n{}))'.format(make_indent(deeper_indent(indent)))
    return formatted

def format_catch(what, indent):
    formatted = '{}(catch {} {})'.format(
        make_indent(indent),
        format_expression(what[1], indent = indent),
        format_expression(what[2], indent = indent),
    )
    return formatted

def format_try(what, indent):
    formatted = '(try {} (\n'.format(
        format_expression(what[1], indent),
    )
    exprs = []
    for each in what[2]:
        exprs.append(format_catch(each, indent = deeper_indent(indent)))
    formatted += '\n'.join(exprs)
    formatted += '))'.format(make_indent(deeper_indent(indent)))
    return formatted

def format_if(what, indent):
    formatted = '(if {} {} {})'.format(
        format_expression(what[1], indent),
        format_expression(what[2], indent, in_if = True),
        format_expression(what[3], indent, in_if = True),
    )
    return formatted

def format_call_impl(fn, args, prefix, indent):
    if type(fn) == list:
        fn = format_dot_path(fn)
    else:
        fn = fn.token
    exprs = [format_expression(each, indent) for each in args]
    prefix = ('' if (prefix is None) else '{} '.format(prefix))
    return prefix + (
        '{} {}'.format(fn, ' '.join(exprs))
        if
        exprs
        else
        '{}'.format(fn)
    )

def format_call(fn, args, indent):
    return '({})'.format(format_call_impl(fn, args, None, indent))

def format_special_call(what, indent):
    prefix = what[0].token
    fn = what[1]
    args = what[2:]
    return '({})'.format(format_call_impl(fn, args, prefix, indent))

def format_operator(what, indent):
    exprs = [format_expression(each, indent) for each in what[1:]]
    return '({} {})'.format(what[0].token, ' '.join(exprs),)

def format_expression(what, indent, in_if = False):
    if type(what) == token_types.Comment:
        return '{}'.format(
            what.token,
        )

    def looks_like_call_expression(what):
        if type(what) != list:
            return False
        like_long_name = (type(what[0]) == list and type(what[0][0]) in (
            token_types.Dot,
            token_types.Name,
        ))
        like_short_name = (type(what[0]) == token_types.Name)
        return (like_long_name or like_short_name)
    if looks_like_call_expression(what):
        return format_call(what[0], what[1:], indent)

    if type(what) == list and type(what[0]) in (
            token_types.Actor,
            token_types.Defer,
            token_types.Tailcall,
            token_types.Watchdog,
        ):
        return format_special_call(what, indent)

    if type(what) in (
            token_types.Name,
            token_types.Module_name,
            token_types.Labeled_parameter_name,
            token_types.Integer,
            token_types.String,
            token_types.Boolean,
            token_types.Float,
            token_types.Timeout,
            ):
        return str(what.token)

    if type(what) == list and (type(what[0]) ==
            token_types.Compound_expression_marker):
        exprs = [
            format_expression(each, indent = deeper_indent(indent))
            for each
            in what[1]
        ]
        return '{{{}\n{}}}'.format(
            ''.join(map(lambda each: '\n{}{}'.format(
                make_indent(deeper_indent(indent)),
                each,
            ), exprs)),
            make_indent(indent),
        )

    if type(what) == list and type(what[0]) == token_types.Let:
        return format_let(what, indent, top_level = False)

    if type(what) == list and type(what[0]) == token_types.Match:
        return format_match(what, indent)

    if type(what) == list and type(what[0]) == token_types.Dot:
        return format_dot_path(what)

    if type(what) == list and type(what[0]) == token_types.Try:
        return format_try(what, indent)

    if type(what) == list and type(what[0]) == token_types.If:
        def has_directly_nested_ifs(what):
            if type(what[2]) == list and type(what[2][0]) == token_types.If:
                return True
            if type(what[3]) == list and type(what[3][0]) == token_types.If:
                return True
            return False
        prefix = ''
        if has_directly_nested_ifs(what) or in_if:
            prefix += '\n{}'.format(make_indent(deeper_indent(indent)))
        return prefix + format_if(what, indent)

    if type(what) == list and type(what[0]) in (
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
            token_types.Pointer_dereference,
            token_types.Or,
            token_types.And,
            token_types.Not,
            token_types.Field_assignment,
        ):
        return format_operator(what, indent)

    if type(what) == list and type(what[0]) == token_types.Struct:
        return '(struct)'

    if type(what) == list and type(what[0]) == token_types.Vector:
        return '(vector)'

    if type(what) == list and type(what[0]) == token_types.Labeled_parameter_name:
        return '({} {})'.format(
            what[0].token,
            format_expression(what[1], indent),
        )

    print(what)
    raise Bad_expression(what[0] if type(what) == list else what)

def format_let_var(what, indent, top_level):
    formatted = '(let {} {})'.format(
        what[1].token,
        format_expression(what[2], indent),
    )
    return formatted

def format_let_fn(what, indent, top_level):
    formatted = '{}(let {} '.format(
        (make_indent(indent) if top_level else ''),
        what[1].token
    )
    formatted += format_formal_parameters(what[2], indent)
    formatted += ' '
    formatted += format_expression(what[3], indent)
    formatted += ')'
    return formatted

def format_let(what, indent, top_level):
    if len(what) == 4:
        return format_let_fn(what, indent, top_level)
    elif len(what) == 3:
        return format_let_var(what, indent, top_level)
    else:
        raise Bad_expression(what)

def format_module(what, indent):
    formatted = '(module {} ({}\n))'.format(
        what[1].token,
        format_source_code_impl(what[2], indent = deeper_indent(indent)),
    )
    return formatted

def format_import(what, indent):
    formatted = '(import {})'.format(
        format_expression(what[1], indent = indent),
    )
    return formatted

def format_source_code_impl(groups, indent):
    formatted = ''

    previous_group = None
    previous_group_leader_t = None
    for each in groups:
        if type(each) == token_types.Comment:
            if previous_group_leader_t != token_types.Comment:
                formatted += '\n'
            formatted += '\n{}{}'.format(
                make_indent(indent),
                each.token,
            )

            previous_group = each
            previous_group_leader_t = token_types.Comment
            continue

        if type(each[0]) == token_types.Enum:
            s = format_enum(each, indent)
            if previous_group_leader_t != token_types.Enum:
                formatted += '\n'
            if previous_group_leader_t is not None:
                formatted += '\n'
            formatted += s
        elif type(each[0]) == token_types.Let:
            s = format_let(each, indent, top_level = True)
            if (previous_group_leader_t is not None and
                    previous_group_leader_t != token_types.Comment):
                formatted += '\n'
            formatted += ('\n' + s)
        elif type(each[0]) == token_types.Module:
            if previous_group_leader_t != token_types.Module:
                formatted += '\n'
            s = format_module(each, indent)
            formatted += ('\n' + s)
        elif type(each[0]) == token_types.Import:
            prev_mod_name = None
            if previous_group_leader_t == token_types.Module:
                prev_mod_name = str(previous_group[1].token)
            import_path = flatten_dot_path(each[1])
            if not (prev_mod_name == str(import_path[0].token) or
                previous_group_leader_t == token_types.Import or
                previous_group_leader_t is not None):
                formatted += '\n'
            s = format_import(each, indent)
            formatted += ('\n' + s)
        elif type(each[0]) == list:
            # This is a dirty hack. Once grouping code is fixed to always return
            # a list of groups and not sometimes a list embedded in an extra
            # list this elif will not be needed.
            formatted += format_source_code_impl(each, indent)
        else:
            print(type(each), each)
            raise Bad_expression(each)

        previous_group = each
        previous_group_leader_t = type(previous_group[0])

    return formatted

def format_source_code(groups, indent_width):
    return format_source_code_impl(groups, (indent_width, 0,)).strip()


def main(executable_name, args):
    if '--version' in args:
        print('{} version {} ({})'.format(
            EXECUTABLE,
            viuact.__version__,
            viuact.__commit__,
        ))
        exit(0)

    if '--help' in args:
        viuact.util.help.print_help(
            EXECUTABLE,
            suite = viuact.suite,
            version = viuact.__version__,
            text = HELP,
        )
        exit(0)

    source_file_name = args[-1]
    source_code = None
    with open(source_file_name, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = lexer.lex(source_code)
    groups = parser.group(tokens)

    indent_width = 4
    if '-s' in args:
        indent_width = int(args[args.index('-s') + 1])

    nice_source_code = format_source_code(groups, indent_width)

    if '-i' in args:
        with open(source_file_name, 'w') as ofstream:
            ofstream.write(nice_source_code + '\n')
    else:
        print(nice_source_code)

main(sys.argv[0], sys.argv[1:])
