#!/usr/bin/env python3

import os
import sys

import viuact
import viuact.frontend
import viuact.driver
import viuact.env


HELP = '''{man_executable}(1)

NAME
    {executable} - Viuact compiler

SYNOPSIS
    {executable} <file>
    {exec_blank} --mode (module | exec | auto) <file>
    {exec_blank} --help

DESCRIPTION
    Compiler from Viuact to Viua VM assembly language. Viuact is a high-level
    programming language with a Lisp-like syntax.

OPTIONS
    --help
        Display this message.

    --version
        Display version information.

    --mode module | exec | auto
        Set compilation mode; 'auto' is the default one.

    --env
        Display information about the environment that the compiler will use.

EXAMPLES
    The canonical program

        $ cat hello.lisp
        (let main () (print "Hello, World!"))
        $ viuact-cc --mode exec hello.lisp
        $ viuact-opt build/_default/hello.asm
        $ viua-vm build/_default/hello.bc
        Hello, World!

SEE ALSO
    viuact-opt(1)

COPYRIGHT
    Copyright (c) 2018-2019 Marek Marecki

    Some parts of the code were developed at Polish-Japanse Academy Of
    Information Technology in Gdańsk, Poland.

    This is Free Software published under GNU GPL v3 license.
'''


def main(executable_name, args):
    if '--version' in args:
        print('{} version {} ({})'.format(
            os.path.split(executable_name)[1],
            viuact.__version__,
            viuact.__commit__,
        ))
        exit(0)

    if '--help' in args:
        executable = os.path.split(executable_name)[1]
        print(HELP.format(
            man_executable = executable.upper(),
            executable = executable,
            exec_blank = (' ' * len(executable)),
        ).strip())
        exit(0)

    if '--env' in args:
        print('DEFAULT_OUTPUT_DIRECTORY: {}'.format(
            viuact.env.DEFAULT_OUTPUT_DIRECTORY,
        ))
        print('STDLIB_HEADERS_DIRECTORY: {}'.format(
            viuact.env.STDLIB_HEADERS_DIRECTORY,
        ))
        if viuact.env.VIUACT_LIBRARY_PATH:
            prefix = 'VIUACT_LIBRARY_PATH:'
            print('{} {}'.format(
                prefix,
                viuact.env.VIUACT_LIBRARY_PATH[0],
            ))
            for each in viuact.env.VIUACT_LIBRARY_PATH[1:]:
                print('{} {}'.format(
                    (len(prefix) * ' '),
                    each,
                ))
        print('VIUA_ASM_PATH: {}'.format(
            viuact.env.VIUA_ASM_PATH,
        ))
        if viuact.env.VIUACT_ASM_FLAGS:
            prefix = 'VIUACT_ASM_FLAGS:'
            print('{} {}'.format(
                prefix,
                viuact.env.VIUACT_ASM_FLAGS[0],
            ))
            for each in viuact.env.VIUACT_ASM_FLAGS[1:]:
                print('{} {}'.format(
                    (len(prefix) * ' '),
                    each,
                ))
        if viuact.env.VIUACT_DUMP_INTERMEDIATE:
            prefix = 'VIUACT_DUMP_INTERMEDIATE:'
            print('{} {}'.format(
                prefix,
                viuact.env.VIUACT_DUMP_INTERMEDIATE[0],
            ))
            for each in viuact.env.VIUACT_DUMP_INTERMEDIATE[1:]:
                print('{} {}'.format(
                    (len(prefix) * ' '),
                    each,
                ))
        exit(0)

    viuact.driver.compile_file(**viuact.frontend.cc(executable_name, args))

main(sys.argv[0], sys.argv[1:])
