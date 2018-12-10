#!/usr/bin/env python3

import json
import sys
import os


import env


VIUA_ASM_PATH = os.environ.get('VIUA_ASM_PATH', '../core/viuavm/build/bin/vm/asm')


def main(args):
    main_file = args[0]
    main_dependency_file = '{}.d'.format(os.path.splitext(main_file)[0])

    print('main file:            {}'.format(main_file))
    print('main dependency file: {}'.format(main_dependency_file))

    main_imports = []
    with open(main_dependency_file, 'r') as ifstream:
        main_imports = json.loads(ifstream.read())['imports']

    if main_imports:
        prefix = 'imports: '
        print('{}{}'.format(prefix, main_imports[0]))

        prefix = ' ' * len(prefix)
        for each in main_imports[1:]:
            print('{}{}'.format(prefix, each))

    import_paths = {}

    for each in main_imports:
        module_source_path = os.path.join(*each.split('::')) + '.asm'
        module_binary_path = os.path.join(*each.split('::')) + '.module'

        print('looking for module {}'.format(each))
        for candidate in env.VIUAC_LIBRARY_PATH:
            candidate_module_source_path = os.path.join(candidate, module_source_path)
            candidate_module_binary_path = os.path.join(candidate, module_binary_path)

            found_source_form = os.path.isfile(candidate_module_source_path)
            found_binary_form = os.path.isfile(candidate_module_binary_path)

            print('    in {}{}'.format(module_source_path, (
                ' (found)' if found_source_form else ''
            )))
            if found_source_form:
                import_paths[each] = candidate_module_source_path
                break

            print('    in {}{}'.format(module_binary_path, (
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

    print(import_paths)


main(sys.argv[1:])
