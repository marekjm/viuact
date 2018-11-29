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


class Compilation_mode:
    Automatic = 'auto'
    Executable = 'exec'
    Module = 'module'

Valid_compilation_modes = (
    Compilation_mode.Automatic,
    Compilation_mode.Executable,
    Compilation_mode.Module,
)


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

    output_directory = './build/_default'
    os.makedirs(output_directory, exist_ok = True)

    print('output directory:    {}'.format(env.DEFAULT_OUTPUT_DIRECTORY))
    print('library search path: {}'.format(' '.join(map(repr, env.VIUAC_LIBRARY_PATH))))

    compile_as = Compilation_mode.Automatic
    source_file = None
    if len(args) == 1:
        source_file = args[0]
    else:
        if args[0] != '--mode':
            print_error('error: unknown option: {}'.format(repr(args[0])))
            print_error('note: run {} --help to get help'.format(executable_name))
            exit(1)

        compile_as = args[1]
        source_file = args[2]

    if compile_as not in Valid_compilation_modes:
        print_error('error: invalid compilation mode: {}'.format(compile_as))
        exit(1)

    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = lexer.strip_comments(lexer.lex(source_code))

    groups = parser.group(tokens)
    if not groups:
        sys.stderr.write('error: source file contains no expressions: {}\n'.format(source_file))
        exit(1)

    expressions = parser.parse(groups)

    module_name = os.path.basename(source_file).split('.')[0]
    compilation_filesystem_root = os.path.dirname(source_file)
    lowered_function_bodies = []
    try:
        if compile_as == Compilation_mode.Module:
            module_name = module_name[0].upper() + module_name[1:]
            print('compiling module: {} (from {})'.format(module_name, source_file))

            module = group_types.Inline_module(name = token_types.Module_name(module_name))
            for each in expressions:
                if type(each) is group_types.Inline_module:
                    module.module_names.append(str(each.name.token))
                    module.modules[module.module_names[-1]] = each
                elif type(each) is group_types.Module:
                    module.module_names.append(str(each.name.token))
                    module.modules[module.module_names[-1]] = each
                elif type(each) is group_types.Function:
                    module.function_names.append(str(each.name.token))
                    module.functions[module.function_names[-1]] = each
                elif type(each) is group_types.Import:
                    module.imports.append(each)
                else:
                    raise Exception('expected `module`, `import`, or `let` keyword, got', each)

            lowered_function_bodies, meta = lowerer.lower_module(
                module_expr = module,
                in_module = (),
                compilation_filesystem_root = compilation_filesystem_root,
            )

            all_modules = set([
                each['from_module']
                for each
                in meta.functions.values()
            ])

            module_function_mapping = {}
            module_contents = {}

            for each in all_modules:
                module_function_mapping[each] = []
                module_contents[each] = []
            for each in meta.functions.values():
                module_function_mapping[each['from_module']].append(each['real_name'])
            for module_name, contained_functions in module_function_mapping.items():
                for fn_name in set(contained_functions):
                    module_contents[module_name].append(
                        list(filter(lambda each: each[0] == fn_name, lowered_function_bodies))[0][1]
                    )

            for module_name, contents in module_contents.items():
                module_path = module_name.split('::')
                if len(module_path) > 1:
                    os.makedirs(os.path.join(output_directory, *module_path[:-1]), exist_ok = True)

                module_impl_path = os.path.join(*module_path) + '.asm'
                print('generating definition for: {} (in {})'.format(module_name, module_impl_path))
                with open(os.path.join(output_directory, module_impl_path), 'w') as ofstream:
                    if meta.signatures:
                        ofstream.write('\n'.join(map(
                            lambda each: '.signature: {}'.format(each),
                            meta.signatures,
                        )))
                        ofstream.write('\n\n')
                    ofstream.write(';\n; Function definitions of module {}\n;\n\n'.format(
                        module_name
                    ))
                    ofstream.write('\n\n'.join(contents))

                module_interface_path = os.path.join(*module_path) + '.i'
                print('generating interface for:  {} (in {})'.format(module_name, module_interface_path))
                fns = [
                    {
                        'arity': v['arity'],
                        'name': k,
                        'real_name': v['real_name'],
                        'from_module': v['from_module'],
                    }
                    for k, v
                    in meta.functions.items()
                    if v['from_module'] == module_name
                ]
                with open(os.path.join(output_directory, module_interface_path), 'w') as ofstream:
                    ofstream.write(json.dumps({ 'fns': fns, }, indent = 4))
        elif compile_as == Compilation_mode.Executable:
            print('compiling executable: {} (from {})'.format(module_name, source_file))

            if not list(filter(lambda each: type(each) is group_types.Function, expressions)):
                print_error('error: compiling as executable, but no functions were defined')
                exit(1)

            lowered_function_bodies, meta = lowerer.lower_file(
                expressions = expressions,
                module_prefix = None,
                compilation_filesystem_root = compilation_filesystem_root,
            )

            all_modules = set([
                each['from_module']
                for each
                in meta.functions.values()
            ])

            module_function_mapping = {}
            module_contents = {}

            for each in all_modules:
                module_function_mapping[each] = []
                module_contents[each] = []
            for each in meta.functions.values():
                module_function_mapping[each['from_module']].append(each['real_name'])
            for mod_name, contained_functions in module_function_mapping.items():
                for fn_name in set(contained_functions):
                    module_contents[mod_name].append(
                        list(filter(lambda each: each[0] == fn_name, lowered_function_bodies))[0][1]
                    )

            for mod_name, contents in module_contents.items():
                if mod_name is None:
                    continue

                module_path = mod_name.split('::')
                if len(module_path) > 1:
                    os.makedirs(os.path.join(output_directory, *module_path[:-1]), exist_ok = True)

                module_impl_path = os.path.join(*module_path) + '.asm'
                print('generating definition for: {} (in {})'.format(module_name, module_impl_path))
                with open(os.path.join(output_directory, module_impl_path), 'w') as ofstream:
                    if meta.signatures:
                        ofstream.write('\n'.join([
                            '.signature: {}'.format(each)
                            for each
                            in meta.signatures
                            if each not in module_function_mapping[mod_name]
                        ]))
                        ofstream.write('\n\n')
                    ofstream.write(';\n; Function definitions of module {}\n;\n\n'.format(
                        mod_name
                    ))
                    ofstream.write('\n\n'.join(contents))

                module_interface_path = os.path.join(*module_path) + '.i'
                print('generating interface for:  {} (in {})'.format(mod_name, module_interface_path))
                fns = [
                    {
                        'arity': v['arity'],
                        'name': k,
                        'real_name': v['real_name'],
                        'from_module': v['from_module'],
                    }
                    for k, v
                    in meta.functions.items()
                    if v['from_module'] == module_name
                ]
                with open(os.path.join(output_directory, module_interface_path), 'w') as ofstream:
                    ofstream.write(json.dumps({ 'fns': fns, }, indent = 4))

            with open(os.path.join(output_directory, '{}.asm'.format(module_name)), 'w') as ofstream:
                if meta.signatures:
                    ofstream.write('\n'.join(map(
                        lambda each: '.signature: {}'.format(each),
                        meta.signatures,
                    )))
                    ofstream.write('\n\n')
                ofstream.write('\n\n'.join([
                    each
                    for (_, each)
                    in lowered_function_bodies
                    if meta.functions.get(_, {}).get('from_module') is None
                ]))
    except (exceptions.Emitter_exception, exceptions.Lowerer_exception,) as e:
        msg, cause = e.args
        line, character = 0, 0

        cause_type = type(cause)
        if cause_type is group_types.Function:
            token = cause.name.token
            line, character = token.location()

        print('{}:{}:{}: {}: {}'.format(
            source_file,
            line + 1,
            character + 1,
            msg,
            cause,
        ))
        raise

main(sys.argv[0], sys.argv[1:])
