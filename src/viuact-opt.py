#!/usr/bin/env python3

import json
import subprocess
import sys
import os


import env
import logs


VIUA_ASM_PATH = os.environ.get('VIUA_ASM_PATH', '../core/viuavm/build/bin/vm/asm')


def main(args):
    main_source_file = args[0]
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

        asm_process = subprocess.Popen(
            args = (env.VIUA_ASM_PATH, '-c', '-o', output_path, source_path),
        )

        asm_exit_code = asm_process.wait()
        if asm_exit_code:
            sys.stderr.write('error: failed to assemble module {}\n'.format(each))
            exit(asm_exit_code)

        library_files_to_link.append(output_path)

    main_output_file = (args[1] if len(args) >= 2 else 'a.out')
    asm_process = subprocess.Popen(
        args = (env.VIUA_ASM_PATH, '-o', main_output_file, main_source_file,) + tuple(library_files_to_link)
    )
    asm_exit_code = asm_process.wait()
    if asm_exit_code:
        exit(asm_exit_code)


main(sys.argv[1:])