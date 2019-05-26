#!/usr/bin/env python3

import sys

import viuact
from viuact import token_types, group_types, lexer, parser

HELP = '''NAME
    viuact-format  -- format ViuAct source code

SYNOPSIS
    viuact-format [ -i ] <file>
                  --version
                  --help

DESCRIPTION
    Format ViuAct source code according to a predefined coding style. This helps
    enforcing a uniform look for all source code.

OPTIONS
    -i
        Edit the file in-place instead of printing formatted source code on
        standard output.

    --version
        Display version information.

    --help
        Display this help screen.
'''

def nicely_format_token_stream(tokens):
    nicely_formatted_source_code = str(tokens[0].token)

    class Any:
        def __eq__(self, x):
            return True
    _ = Any()

    last_token = tokens[0]

    indent_level = 0
    indent_string = '    '

    paren_level = 0
    paren_level_event_fire_on = []

    EVENT_TEXT = 0
    EVENT_INDENT = 1
    EVENT_DEDENT = 2
    TRIGGER_PAREN_LEVEL = 0

    for each in tokens[1:]:
        lt = type(last_token)
        et = type(each)
        tt = token_types

        for event in paren_level_event_fire_on:
            if event[0] == (TRIGGER_PAREN_LEVEL, paren_level):
                if event[1] == EVENT_TEXT:
                    if event[2][0] == '\b':
                        nicely_formatted_source_code = nicely_formatted_source_code[:-1] + event[2][1:]
                    else:
                        nicely_formatted_source_code += event[2]
                elif event[1] == EVENT_INDENT:
                    indent_level += 1
                elif event[1] == EVENT_DEDENT:
                    indent_level -= 1

        paren_level_event_fire_on = list(filter(lambda ev: ev[0] != (TRIGGER_PAREN_LEVEL, paren_level), paren_level_event_fire_on))

        if et == tt.Right_curly:
            indent_level -= 1
            nicely_formatted_source_code += '\n' + (indent_string * indent_level)

        pat = (lt, et,)
        if pat == (tt.Left_paren, tt.Let) or pat == (tt.Left_paren, tt.Right_paren):
            nicely_formatted_source_code += str(each.token)
        elif pat == (tt.Right_paren, tt.Left_paren) or pat == (tt.Left_paren, tt.Left_paren):
            nicely_formatted_source_code += '\n' + (indent_string * indent_level) + str(each.token)
        elif pat == (tt.Left_paren, tt.Module):
            indent_level += 1
            nicely_formatted_source_code = nicely_formatted_source_code[:-1] + '\n(' + str(each.token)
        elif pat == (tt.Left_paren, _) or pat == (_, tt.Right_paren):
            nicely_formatted_source_code += str(each.token)
        elif pat == (tt.Left_curly, _) or pat == (_, tt.Right_curly):
            nicely_formatted_source_code += str(each.token)
        elif pat == (_, tt.Dot) or pat == (tt.Dot, _):
            nicely_formatted_source_code += str(each.token)
        else:
            nicely_formatted_source_code += ' ' + str(each.token)

        if pat == (tt.Module_name, tt.Left_paren):
            paren_level_event_fire_on.append((
                (TRIGGER_PAREN_LEVEL, paren_level),
                EVENT_TEXT,
                '\b\n)',
            ))
        if et == tt.Module:
            paren_level_event_fire_on.append((
                (TRIGGER_PAREN_LEVEL, paren_level - 1),
                EVENT_TEXT,
                '\n',
            ))
            paren_level_event_fire_on.append((
                (TRIGGER_PAREN_LEVEL, paren_level - 1),
                EVENT_DEDENT,
            ))

        if et == tt.Left_paren:
            paren_level += 1
        if et == tt.Right_paren:
            paren_level -= 1
        last_token = each

        if et == tt.Left_curly:
            indent_level += 1
            nicely_formatted_source_code += '\n' + (indent_string * indent_level)

    return nicely_formatted_source_code.lstrip()

def main(args):
    if '--version' in args:
        print(viuact.__version__)
        exit(0)
    if '--help' in args:
        print(HELP)
        exit(0)

    source_file_name = args[-1]
    source_code = None
    with open(source_file_name, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = lexer.lex(source_code)

    nice_source_code = nicely_format_token_stream(tokens)
    if '-i' in args:
        with open(source_file_name, 'w') as ofstream:
            ofstream.write(nice_source_code)
    else:
        print(nice_source_code)

main(sys.argv[1:])
