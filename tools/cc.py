#!/usr/bin/env python3

import json
import os
import sys

import viuact.util.help
import viuact.util.log
import viuact.errors
import viuact.lexer
import viuact.parser
import viuact.core


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

    %opt(--env)
        %text
        Display information about the environment that the compiler will use.

    %opt(-t), %opt(--tokenise)
        %text
        Stop after tokenisation and output JSON dump to standard output.

    %opt(-p), %opt(--parse)
        %text
        Stop after parsing and output JSON dump to standard output.

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


def report_error(source_file_name, e, human = True):
    viuact.util.log.error(
        s = e.what(),
        path = source_file_name,
        pos = e.at(human = human),
    )
    for each in e.notes():
        viuact.util.log.note(
            s = each,
            path = source_file_name,
            pos = e.at(human = human),
        )

    for each in e.fallout():
        report_error(source_file_name, e, human)

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

    source_file_arg_index = 0
    stop_after_tokenisation = False
    stop_after_parsing = False
    if args[source_file_arg_index] in ('-t', '--tokenise', '-p', '--parse',):
        stop_after_tokenisation = (
            args[source_file_arg_index] in ('-t', '--tokenise',))
        stop_after_parsing = (
            args[source_file_arg_index] in ('-p', '--parse',))
        source_file_arg_index = 1

    source_file = args[source_file_arg_index]
    if not os.path.isfile(source_file):
        viuact.util.log.error('not a file: {}'.format(
            viuact.util.colors.colorise_repr('white', source_file)))
        exit(1)

    source_text = ''
    with open(source_file, 'r') as ifstream:
        source_text = ifstream.read()


    ############################################################################
    # LEXICAL AND SYNTACTICAL ANALYSIS
    #   a.k.a. lexing and parsing
    try:
        tokens = viuact.lexer.lex(source_text)
        if stop_after_tokenisation:
            print(json.dumps(viuact.lexer.to_data(tokens), indent = 2))
            exit(0)

        forms = viuact.parser.parse(tokens)
        if stop_after_parsing:
            print(json.dumps(viuact.parser.to_data(forms), indent = 2))
            exit(0)

        module_name = viuact.core.EXEC_MODULE
        output_directory = 'build/_default'

        source_file = os.path.normpath(source_file)

        DEFAULT_SOURCE_ROOT = '.'
        source_root = os.path.normpath(
            args[source_file_arg_index + 1]
            if len(args) > (source_file_arg_index + 1) else
            DEFAULT_SOURCE_ROOT
        )
        if (not os.path.isabs(source_file)) and source_root == DEFAULT_SOURCE_ROOT:
            source_file = os.path.join(DEFAULT_SOURCE_ROOT, source_file)

        if not source_file.startswith(source_root):
            raise viuact.errors.Fail(
                (0, 0,), 'source file not in source root'
            ).note(
                'source file: {}'.format(source_file)
            ).note(
                'source root: {}'.format(source_root)
            )

        viuact.core.cc(
            source_root,
            source_file,
            module_name,
            forms,
            output_directory,
        )
    except viuact.errors.Error as e:
        report_error(source_file, e, human = True)
        exit(1)

main(sys.argv[0], sys.argv[1:])
