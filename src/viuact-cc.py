#!/usr/bin/env python3

import collections
import json
import os
import re
import sys


import token_types
import group_types
import exceptions
import lexer
import parser
import lowerer
import env
import logs
import driver


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

    driver.compile(executable_name, args)

main(sys.argv[0], sys.argv[1:])
