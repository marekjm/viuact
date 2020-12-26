#!/usr/bin/env python3

import os
import subprocess
import sys

import viuact.util.help
import viuact.util.log


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

    %text
    This is Free Software published under GNU GPL v3 license.
'''


EXECUTABLE = 'viuact-opt'


SOURCE_KIND_EXEC = 'exec'
SOURCE_KIND_LINK = 'link'

def determine_source_kind(source_file):
    file_name = os.path.split(source_file)[1]
    if (file_name[0].isupper() or file_name == 'mod.asm'):
        return SOURCE_KIND_LINK
    return SOURCE_KIND_EXEC

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

    source_path = args[-1]
    if not os.path.isfile(source_path):
        viuact.util.log.error('not a file: {}'.format(
            viuact.util.colors.colorise_repr('white', source_path)))
        exit(1)

    assembler_args = [
        'viua-asm',
        '-Wunused-value',
        '-Wunused-register',
    ]

    extension = 'bc'
    if determine_source_kind(source_path) == SOURCE_KIND_LINK:
        assembler_args.append('-c')
        extension = 'module'

    output_path = '{}.{}'.format(
        source_path.rsplit('.', maxsplit = 1)[0],
        extension,
    )
    assembler_args.extend(['-o', output_path])

    assembler_args.append(source_path)

    viuact.util.log.debug(' '.join(assembler_args))

    assembler_run = subprocess.Popen(
        args = tuple(assembler_args),
    )
    ret = assembler_run.wait()
    if ret != 0:
        viuact.util.log.error('assembly rejected')
        exit(1)


main(sys.argv[0], sys.argv[1:])
