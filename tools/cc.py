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
    {exec_tool} src/%arg(file).vt
    {exec_blank} -r src src/%arg(file).vt
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

    %opt(-r)
        %text
        Override source root inferred by the compiler.

        %text
        Use this option if the compiler incorrectly infers the source root (ie,
        the directory which is the root of a module structure for Viuact
        program).

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

        %fg(source)(val main () -> i64)
        %fg(source)(let main () {{
        %fg(source)    (print "Hello, World!")
        %fg(source)    0
        %fg(source)}})

    %fg(man_se)CONDITIONAL EXECUTION - IF%r

        %fg(source)(val main () -> i64)
        %fg(source)(let main () {{
        %fg(source)    (let x true)
        %fg(source)    (let result (if x "It's true!" "It's false..."))
        %fg(source)    (print result)
        %fg(source)    0
        %fg(source)}})

    %fg(man_se)CONDITIONAL EXECUTION - MATCH%r

        %fg(source)(enum option (
        %fg(source)    (Some 'a)
        %fg(source)    None
        %fg(source)))

        %fg(source)(val main () -> i64)
        %fg(source)(let main () {{
        %fg(source)    (let answer (option::Some 42))
        %fg(source)    (print (match answer (
        %fg(source)        ; only contructor names needed since the compiler
        %fg(source)        ; knows the type at this point
        %fg(source)        (with Some value (.. "The answer is: " value))
        %fg(source)        (with None       "Only questions..."))))
        %fg(source)    0
        %fg(source)}})

    %fg(man_se)CALLING FUNCTIONS%r

        %fg(source)(val ('a) greet ('a) -> string)
        %fg(source)(let greet (someone) {{
        %fg(source)    ; Construct and print the greeting...
        %fg(source)    (let greeting (.. "Hello, " someone "!"))
        %fg(source)    (print greeting)
        %fg(source)    ; ...then use it as the return value.
        %fg(source)    greeting
        %fg(source)}})

        %fg(source)(let main () {{
        %fg(source)    ; the 'a parameter is polymorphic so accepts strings and
        %fg(source)    ; integers
        %fg(source)    (greet "World")
        %fg(source)    (greet 42)
        %fg(source)    0
        %fg(source)}})

{COPYRIGHT}
    %copyright(2018-2020) Marek Marecki

    %text
    Some parts of the code were developed at Polish-Japanse Academy Of
    Information Technology in Gdańsk, Poland.

    %text
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

def parse_options(args):
    options = {
        'source_root': '.',
        'stop_after_tokenisation': False,
        'stop_after_parsing': False,
        'show_env': False,
    }

    i = 0
    while i < len(args):  # -1 because skip the source file
        each = args[i]

        if each == '-r':
            i += 1
            options['source_root'] = args[i]
        elif each in ('-t', '--tokenise',):
            options['stop_after_tokenisation'] = True
        elif each in ('-p', '--parse',):
            options['stop_after_parsing'] = True
        elif each in ('--env',):
            options['show_env'] = True
        else:
            break

        i += 1

    source_file = None
    if i < len(args):
        source_file = args[i]

    return (options, source_file,)

DEFAULT_SOURCE_ROOT = '.'

SOURCE_KIND_EXEC = 'exec'
SOURCE_KIND_LINK = 'link'

def get_source_location(options, raw_path):
    working_directory = (os.getcwd() + os.path.sep)

    source_root = options['source_root']
    source_root = (os.path.normpath(os.path.abspath(source_root))
            + os.path.sep)
    source_root = (source_root.replace(working_directory, '') or
            DEFAULT_SOURCE_ROOT)

    used_path = os.path.normpath(os.path.abspath(raw_path))
    used_path = used_path.replace(working_directory, '')
    # print('used: {}'.format(used_path))

    if options['source_root'] != DEFAULT_SOURCE_ROOT:
        return (
            os.path.normpath(source_root),
            os.path.normpath(used_path.replace(source_root, '')),
        )

    parts = used_path.split(os.path.sep)
    parts.reverse()
    # print('part: {}'.format(parts))

    source_file_parts = [parts[0]]
    for each in parts[1:]:
        if each[0].islower():
            break
        source_file_parts.append(each)
    source_file_parts.reverse()

    source_file = os.path.sep.join(source_file_parts)

    source_root = parts[len(source_file_parts):]
    source_root.reverse()
    source_root = os.path.sep.join(source_root)

    return (
        os.path.normpath(source_root),
        os.path.normpath(source_file),
    )

def determine_source_kind(source_file):
    file_name = os.path.split(source_file)[1]
    if (file_name[0].isupper() or file_name == 'mod.vt'):
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

    if len(args) == 0:
        viuact.util.log.error('no source file given')
        viuact.util.log.note('use --help to learn about correct invocation')
        exit(1)

    options, source_file = parse_options(args)
    if options['show_env']:
        print('VIUACT_DEBUG={}'.format(os.environ.get('VIUACT_DEBUG', 'false')))
        print('VIUACT_LIBRARY_PATH={}'.format(viuact.env.library_path()))
        print('VIUACT_CORE_DIR={}'.format(viuact.env.core_directory('')))
        print('VIUACT_OUTPUT_DIR={}'.format(viuact.env.output_directory()))
        return 0

    if source_file is None:
        viuact.util.log.error('no source file given')
        viuact.util.log.note('use --help to learn about correct invocation')
        exit(1)

    source_root, source_file = get_source_location(options, source_file)
    source_kind = determine_source_kind(source_file)

    # print('file: {}'.format(source_file))
    # print('root: {}'.format(source_root))
    # print('kind: {}'.format(source_kind))

    source_full_path = os.path.join(source_root, source_file)
    if not os.path.isfile(source_full_path):
        viuact.util.log.error('not a file: {}'.format(
            viuact.util.colors.colorise_repr('white', source_full_path)))
        exit(1)

    source_text = ''
    with open(source_full_path, 'r') as ifstream:
        source_text = ifstream.read()

    ############################################################################
    # LEXICAL AND SYNTACTICAL ANALYSIS
    #   a.k.a. lexing and parsing
    try:
        tokens = viuact.lexer.lex(source_text)
        if options['stop_after_tokenisation']:
            print(json.dumps(viuact.lexer.to_data(tokens), indent = 2))
            exit(0)

        forms = viuact.parser.parse(tokens)
        if options['stop_after_parsing']:
            print(json.dumps(viuact.parser.to_data(forms), indent = 2))
            exit(0)

        module_name = (
            viuact.core.EXEC_MODULE
            if (source_kind == SOURCE_KIND_EXEC) else
            source_file.rsplit('.', maxsplit = 1)[0].replace('/', '::')
        )

        output_directory = viuact.env.output_directory()

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
