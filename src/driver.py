import collections
import json
import os
import re
import subprocess
import sys


import token_types
import group_types
import exceptions
import lexer
import parser
import lowerer
import env
import logs


class Compilation_mode:
    Automatic = 'auto'
    Executable = 'exec'
    Module = 'module'

Valid_compilation_modes = (
    Compilation_mode.Automatic,
    Compilation_mode.Executable,
    Compilation_mode.Module,
)


def compile_text(
        executable_name,
        source_file,
        source_code,
        compile_as,
        output_directory = './build/_default',
        ):
    tokens = lexer.strip_comments(lexer.lex(source_code))

    groups = parser.group(tokens)
    if not groups:
        sys.stderr.write('error: source file contains no expressions: {}\n'.format(source_file))
        exit(1)

    expressions = parser.parse(groups)

    module_name = os.path.basename(source_file).split('.')[0]
    compilation_filesystem_root = os.path.dirname(source_file)
    lowered_function_bodies = []

    main_module_output_name = os.path.join(output_directory, '{}.asm'.format(module_name))
    try:
        if compile_as == Compilation_mode.Module:
            module_name = module_name[0].upper() + module_name[1:]
            logs.verbose('compiling module: {} (from {})'.format(module_name, source_file))

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
                logs.debug('generating definition for: {} (in {})'.format(module_name, module_impl_path))
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
                logs.debug('generating interface for:  {} (in {})'.format(module_name, module_interface_path))
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
            logs.verbose('compiling executable: {} (from {})'.format(module_name, source_file))

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
                    res = list(filter(lambda each: each[0] == fn_name, lowered_function_bodies))
                    if res:
                        module_contents[mod_name].append(
                            res[0][1]
                        )

            for mod_name, contents in module_contents.items():
                if mod_name is None:
                    continue

                # Module is a pure import.
                # If its name is not in modules defined in this file do
                # not emit files for it.
                if mod_name not in meta.modules:
                    logs.debug('module {} is a pure import'.format(mod_name))
                    continue

                module_path = mod_name.split('::')
                if len(module_path) > 1:
                    os.makedirs(os.path.join(output_directory, *module_path[:-1]), exist_ok = True)

                module_impl_path = os.path.join(*module_path) + '.asm'
                logs.debug('generating definition for: {} (in {})'.format(mod_name, module_impl_path))
                with open(os.path.join(output_directory, module_impl_path), 'w') as ofstream:
                    if meta.signatures:
                        ofstream.write('\n'.join([
                            '.signature: {}'.format(each)
                            for each
                            in meta.signatures
                            if each.split('/')[0] not in module_function_mapping[mod_name]
                        ]))
                        ofstream.write('\n\n')
                    ofstream.write(';\n; Function definitions of module {}\n;\n\n'.format(
                        mod_name
                    ))
                    ofstream.write('\n\n'.join(contents))

                module_interface_path = os.path.join(*module_path) + '.i'
                logs.debug('generating interface for:  {} (in {})'.format(mod_name, module_interface_path))
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

            with open(main_module_output_name, 'w') as ofstream:
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

            with open(os.path.join(output_directory, '{}.d'.format(module_name)), 'w') as ofstream:
                ofstream.write(json.dumps({
                    'imports': meta.imports,
                }, indent = 2))
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

    return main_module_output_name

def compile_file(
        executable_name,
        args,
        source_file,
        compile_as,
        output_directory = './build/_default',
        ):
    os.makedirs(output_directory, exist_ok = True)

    logs.info('output directory:    {}'.format(env.DEFAULT_OUTPUT_DIRECTORY))
    logs.info('library search path: {}'.format(' '.join(map(repr, env.VIUAC_LIBRARY_PATH))))

    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    return compile_text(
        executable_name = executable_name,
        source_file = source_file,
        source_code = source_code,
        compile_as = compile_as,
        output_directory = output_directory,
    )

def assemble_and_link(main_source_file, main_output_file):
    main_dependency_file = '{}.d'.format(os.path.splitext(main_source_file)[0])

    logs.verbose('main file:            {}'.format(main_source_file))
    logs.verbose('main dependency file: {}'.format(main_dependency_file))

    main_imports = []
    with open(main_dependency_file, 'r') as ifstream:
        main_imports = json.loads(ifstream.read())['imports']

    if main_imports:
        prefix = 'imports: '
        logs.verbose('{}{}'.format(prefix, main_imports[0]))

        prefix = ' ' * len(prefix)
        for each in main_imports[1:]:
            logs.verbose('{}{}'.format(prefix, each))

    import_paths = {}

    for each in main_imports:
        module_source_path = os.path.join(*each.split('::')) + '.asm'
        module_binary_path = os.path.join(*each.split('::')) + '.module'

        logs.debug('looking for module {}'.format(each))
        for candidate in env.VIUAC_LIBRARY_PATH:
            candidate_module_source_path = os.path.join(candidate, module_source_path)
            candidate_module_binary_path = os.path.join(candidate, module_binary_path)

            found_source_form = os.path.isfile(candidate_module_source_path)
            found_binary_form = os.path.isfile(candidate_module_binary_path)

            logs.debug('    in {}{}'.format(module_source_path, (
                ' (found)' if found_source_form else ''
            )))
            if found_source_form:
                import_paths[each] = candidate_module_source_path
                break

            logs.debug('    in {}{}'.format(module_binary_path, (
                ' (found)' if found_binary_form else ''
            )))
            if found_binary_form:
                import_paths[each] = candidate_module_binary_path
                break

        if each not in import_paths:
            sys.stderr.write('error: could not find module {}\n'.format(each))
            sys.stderr.write('note: put the directory containing module\'s .asm or\n')
            sys.stderr.write('      .module files in VIUAC_OUTPUT_DIRECTORY env variable\n')
            exit(1)

    library_files_to_link = []
    for each in main_imports:
        source_path = import_paths[each]
        output_path = '{}.out'.format(os.path.splitext(source_path)[0])
        logs.debug('assembling: {} -> {}'.format(source_path, output_path))

        asm_process_args = (
            env.VIUA_ASM_PATH,
            '-Wunused-register',
            '-c',
            '-o',
            output_path,
            source_path,
        )
        logs.debug(' '.join(asm_process_args))
        asm_process = subprocess.Popen(
            args = asm_process_args,
        )

        asm_exit_code = asm_process.wait()
        if asm_exit_code:
            sys.stderr.write('error: failed to assemble module {}\n'.format(each))
            exit(asm_exit_code)

        library_files_to_link.append(output_path)

    asm_process_args = (
        env.VIUA_ASM_PATH,
        '-Wunused-register',
        '-o',
        main_output_file,
        main_source_file,
    ) + tuple(library_files_to_link)
    logs.debug(' '.join(asm_process_args))
    asm_process = subprocess.Popen(
        args = asm_process_args,
    )
    asm_exit_code = asm_process.wait()
    if asm_exit_code:
        exit(asm_exit_code)
