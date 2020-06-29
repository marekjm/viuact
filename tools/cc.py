#!/usr/bin/env python3

import os
import sys

import viuact.util.help


HELP = '''{NAME}
    {executable} - compile Viuact source code into Viua VM assembly language

{SYNOPSIS}
    {exec_tool} --mode %arg(mode) %arg(file).vt
    {exec_blank} --version
    {exec_blank} --help

{DESCRIPTION}
    %text
    Compiler from Viuact to Viua VM assembly language. Viuact is a high-level
    programming language with a Lisp-like syntax.

{OPTIONS}
    %opt(--help)
        Display this message.

    %opt(--version)
        Display version information.

    %opt(--mode) %fg(arg)module%r | %fg(arg)exec%r
        %text
        Set compilation mode. Use %fg(arg)exec%r for modules that should
        produce executables; use %fg(arg)module%r for libraries.

    %opt(--env)
        %text
        Display information about the environment that the compiler will use.

{EXAMPLES}
    %text
    To produce an executable (executable with Viua VM) file from a file
    %fg(const)example.vt%r run the following sequence of commands:

        %fg(source)$ viuact cc --mode exec example.vt
        %fg(source)$ viuact link build/_default/example.asm

    %text
    Assuming there were no errors during compilation, assemby, or linking,
    Viua VM bytecode should be output to %fg(const)build/_default/example.bc%r
    file. To run the produced executable use the following command:

        %fg(source)$ viua-vm build/_default/example.bc

    %fg(man_se)THE CANONICAL PROGRAM%r

        %fg(source)(let main () {{
        %fg(source)    (print "Hello, World!")
        %fg(source)    0
        %fg(source)}})

    %fg(man_se)CONDITIONAL EXECUTION - IF%r

        %fg(source)(let main () {{
        %fg(source)    (let x true)
        %fg(source)    (let result (if x "It's true!" "It's false..."))
        %fg(source)    (print result)
        %fg(source)    0
        %fg(source)}})

    %fg(man_se)CONDITIONAL EXECUTION - MATCH%r

        %fg(source)(enum Maybe (
        %fg(source)    (Some _)
        %fg(source)    None
        %fg(source)))

        %fg(source)(let main () {{
        %fg(source)    (let answer (Maybe.Some 42))
        %fg(source)    (print (match answer (
        %fg(source)        (with Maybe.Some value {{
        %fg(source)            (let value' (Std.String.to_string value))
        %fg(source)            (Std.String.concat "The answer is: " value')
        %fg(source)        }})
        %fg(source)        (with Maybe.None "Only questions..."))))
        %fg(source)    0
        %fg(source)}})

    %fg(man_se)CALLING FUNCTIONS%r

        %fg(source)(let greet (someone) {{
        %fg(source)    ; Ensure someone is a string.
        %fg(source)    (let someone' (Std.String.to_string someone))

        %fg(source)    (let greeting (Std.String.concat "Hello, " someone'))
        %fg(source)    (let greeting (Std.String.concat greeting "!"))
        %fg(source)    (print greeting)

        %fg(source)    ; Use the greeting string as the return value.
        %fg(source)    greeting
        %fg(source)}})

        %fg(source)(let main () {{
        %fg(source)    (greet "World")
        %fg(source)    0
        %fg(source)}})

{COPYRIGHT}
    %copyright(2018-2020) Marek Marecki

    %text
    Some parts of the code were developed at Polish-Japanse Academy Of
    Information Technology in Gdańsk, Poland.

    This is Free Software published under GNU GPL v3 license.
'''


EXECUTABLE = 'viuact-cc'


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

main(sys.argv[0], sys.argv[1:])
