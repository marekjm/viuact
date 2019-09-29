#!/usr/bin/env python3

import os
import sys

import viuact
import viuact.driver


HELP = '''{man_executable}(1)

NAME
    {executable} - Viuact linker

SYNOPSIS
    {executable} build/_default/<file>.asm
    {exec_blank} --help

DESCRIPTION
    The "linker" drives the Viua VM assembler to convert files emitted by Viuact
    compiler into bytecode modules, and then link them into an executable.

OPTIONS
    --help
        Display this message.

    --version
        Display version information.

EXAMPLES
    The canonical program

        $ cat hello.lisp
        (let main () (print "Hello, World!"))
        $ viuact-cc --mode exec hello.lisp
        $ viuact-opt build/_default/hello.asm
        $ viua-vm build/_default/hello.bc
        Hello, World!

SEE ALSO
    viuact-cc(1)

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

    viuact.driver.assemble_and_link(
        main_source_file = args[0],
        main_output_file = (args[1] if len(args) >= 2 else None),
    )


main(sys.argv[0], sys.argv[1:])
