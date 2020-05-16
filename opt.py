#!/usr/bin/env python3

import os
import sys

import viuact
import viuact.driver
import viuact.util.help


HELP = '''{NAME}
    {executable} - output Viua VM bytecode

{SYNOPSIS}
    {exec_tool} build/_default/%fg(arg)FILE%r.asm
    {exec_blank} --help
    {exec_blank} --version

{DESCRIPTION}
    %text
    The %fg(man_const)opt%r tool uses the Viua VM assembler to produce bytecode
    modules from .asm files produced by %fg(man_const)viuact cc%r.

{OPTIONS}
    %opt(--help)
        Display this message.

    %opt(--version)
        Display version information.

{COPYRIGHT}
    %copyright(2018-2020) Marek Marecki

    %text
    Some parts of the code were developed at Polish-Japanse Academy Of
    Information Technology in Gdańsk, Poland.

    This is Free Software published under GNU GPL v3 license.
'''


EXECUTABLE = 'viuact-opt'


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

    viuact.driver.assemble_and_link(
        main_source_file = args[0],
        main_output_file = (args[1] if len(args) >= 2 else None),
    )


main(sys.argv[0], sys.argv[1:])
