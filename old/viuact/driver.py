import collections
import hashlib
import json
import os
import re
import subprocess
import sys


from viuact import token_types, group_types, exceptions, lexer, parser, lowerer, env, logs


class Compilation_mode:
    Automatic = 'auto'
    Executable = 'exec'
    Module = 'module'

Valid_compilation_modes = (
    Compilation_mode.Automatic,
    Compilation_mode.Executable,
    Compilation_mode.Module,
)


class Report:
    @staticmethod
    def error(source_file, error):
        token = error.main_token
        while isinstance(token, (token_types.Token_type,)):
            token = token.token

        error_message = 'error: {file}:{line}:{offset}: {error_message}'.format(
            file = source_file,
            line = ((token.line + 1) if token is not None else '?'),
            offset = ((token.character + 1) if token is not None else '?'),
            error_message = error.message(),
        )
        if token is not None:
            error_message += ': {detail}'.format(
                detail = repr(token._text),
            )
        print(error_message)

    @staticmethod
    def error_fallout(source_file, error):
        Report.error(source_file, error)

        cause = error.cause
        if cause is None:
            return

        print('  ...caused by')
        if type(cause) is exceptions.Fallout:
            Report.error_fallout(source_file, cause)
        else:
            Report.error(source_file, cause)


def dump_intermediates(output_directory, source_file, module_name, tokens, expressions):
    if env.Dump_intermediate.Tokens in env.VIUACT_DUMP_INTERMEDIATE:
        intermediate_tokens_path = os.path.join(output_directory, '{}.tokens'.format(module_name))
        with open(intermediate_tokens_path, 'w') as ofstream:
            ofstream.write(json.dumps({
                'source_file': source_file,
                'tokens': list(map(lexer.to_data, tokens)),
            }, indent = 4))

    if env.Dump_intermediate.Expressions in env.VIUACT_DUMP_INTERMEDIATE:
        intermediate_exprs_path = os.path.join(output_directory, '{}.expressions'.format(module_name))
        with open(intermediate_exprs_path, 'w') as ofstream:
            ofstream.write(json.dumps({
                'source_file': source_file,
                'expressions': list(map(lambda each: each.to_data(), expressions)),
            }, indent = 2))

def compile_as_module(
        source_module_name,
        source_file,
        expressions,
        compilation_filesystem_root,
        output_directory,
        ):
    source_module_name = source_module_name[0].upper() + source_module_name[1:]
    main_module_name = source_module_name[0].upper() + source_module_name[1:]
    logs.verbose('compiling module: {} (from {})'.format(source_module_name, source_file))

    module = group_types.Inline_module(name = token_types.Module_name(source_module_name))
    for each in expressions:
        if type(each) is group_types.Inline_module:
            module.module_names.append(str(each.name.token))
            module.modules[module.module_names[-1]] = each
        elif type(each) is group_types.Module:
            module.module_names.append(str(each.name.token))
            module.modules[module.module_names[-1]] = each
        elif type(each) is group_types.Enum_definition:
            module.enums.append(each)
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

    module_name = main_module_name

    fns = [
        fn['real_name']
        for fn
        in meta.functions.values()
        if fn['from_module'] == module_name
    ]
    contents = []
    for fn in fns:
        result = list(filter(lambda x: x[0] == fn, lowered_function_bodies))
        if result:
            contents.append(result[0][1])

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
            'params': [ str(p.token) for p in v['params'] ],
        }
        for k, v
        in meta.functions.items()
        if v['from_module'] == module_name
    ]
    enums = [
        {
            'name': k,
            **v
        }
        for k, v
        in meta.enums.items()
        if v['from_module'] == module_name
    ]
    with open(os.path.join(output_directory, module_interface_path), 'w') as ofstream:
        ofstream.write(json.dumps({
            'foreign': False,
            'real_name': module_name,
            'fns': fns,
            'enums': enums,
        }, indent = 4))

def compile_as_executable(
        source_module_name,
        source_file,
        expressions,
        compilation_filesystem_root,
        main_module_output_name,
        output_directory,
        ):
    logs.verbose('compiling executable: {} (from {})'.format(source_module_name, source_file))

    if not list(filter(lambda each: type(each) is group_types.Function, expressions)):
        print_error('error: compiling as executable, but no functions were defined')
        exit(1)

    lowered_function_bodies, meta = lowerer.lower_file(
        expressions = expressions,
        module_prefix = None,
        compilation_filesystem_root = compilation_filesystem_root,
    )

    for mod_name in meta.modules:
        fns = [
            fn['real_name']
            for fn
            in meta.functions.values()
            if fn['from_module'] == mod_name
        ]
        contents = []
        for fn in fns:
            result = list(filter(lambda x: x[0] == fn, lowered_function_bodies))
            if result:
                contents.append(result[0][1])


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
                    in sorted(meta.signatures)
                    if each.split('/')[0] not in fns
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
                'arity': meta.functions[k]['arity'],
                'name': k,
                'real_name': meta.functions[k]['real_name'],
                'from_module': meta.functions[k]['from_module'],
            }
            for k
            in sorted(meta.functions.keys())
            if meta.functions[k]['from_module'] == source_module_name
        ]
        enums = [
            {
                'name': k,
                **v
            }
            for k, v
            in meta.enums.items()
            if v['from_module'] == mod_name
        ]
        with open(os.path.join(output_directory, module_interface_path), 'w') as ofstream:
            ofstream.write(json.dumps({
                'foreign': False,
                'real_name': mod_name,
                'fns': fns,
                'enums': enums,
            }, indent = 4))

    with open(main_module_output_name, 'w') as ofstream:
        ffi_imports = list(filter(lambda each: each['foreign'], meta.imports))
        if ffi_imports:
            ofstream.write('\n'.join(map(
                lambda each: '.import: [[dynamic]] {}'.format(each['real_name']),
                ffi_imports,
            )))
            ofstream.write('\n\n')

        if meta.signatures:
            ofstream.write('\n'.join(map(
                lambda each: '.signature: {}'.format(each),
                sorted(meta.signatures),
            )))
            ofstream.write('\n\n')

        fns = {}
        for name, body in lowered_function_bodies:
            fns[name] = body
        ofstream.write('\n\n'.join([
            fns[name]
            for name
            in sorted(fns.keys())
            if meta.functions.get(name, {}).get('from_module') is None
        ]))

    with open(os.path.join(output_directory, '{}.d'.format(source_module_name)), 'w') as ofstream:
        ofstream.write(json.dumps({
            'imports': meta.imports,
        }, indent = 2))

def compile_text(
        executable_name,
        source_file,
        source_code,
        compile_as,
        output_directory = './build/_default',
        ):
    tokens = lexer.strip_comments(lexer.lex(source_code))

    groups = None
    try:
        groups = parser.group(tokens)
    except exceptions.Viuact_exception as e:
        raise exceptions.Fallout(
            token = e.main_token,
            message = 'failure during grouping',
            cause = e,
        )
    if not groups:
        sys.stderr.write('error: source file contains no expressions: {}\n'.format(source_file))
        exit(1)

    module_name = os.path.basename(source_file).split('.')[0]
    source_module_name = os.path.basename(source_file).split('.')[0]
    source_module_hash = hashlib.sha1(repr(groups).encode('utf-8')).hexdigest()

    logs.debug('module name:        {}'.format(module_name))
    logs.debug('source module name: {}'.format(source_module_name))
    logs.debug('source module hash: {}'.format(source_module_hash))

    expressions = parser.parse(groups)

    dump_intermediates(output_directory, source_file, source_module_name, tokens, expressions)

    compilation_filesystem_root = os.path.dirname(source_file)
    lowered_function_bodies = []

    main_module_output_name = os.path.join(output_directory, '{}.asm'.format(source_module_name))
    logs.debug('main output file:   {}'.format(main_module_output_name))

    try:
        if compile_as == Compilation_mode.Module:
            compile_as_module(
                source_module_name,
                source_file,
                expressions,
                compilation_filesystem_root,
                output_directory,
            )
        elif compile_as == Compilation_mode.Executable:
            compile_as_executable(
                source_module_name,
                source_file,
                expressions,
                compilation_filesystem_root,
                main_module_output_name,
                output_directory,
            )
    except exceptions.Invalid_number_of_arguments as e:
        msg = e.message()
        cause = e.cause()
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
    logs.info('library search path: {}'.format(' '.join(map(repr, env.VIUACT_LIBRARY_PATH))))

    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    try:
        return compile_text(
            executable_name = executable_name,
            source_file = source_file,
            source_code = source_code,
            compile_as = compile_as,
            output_directory = output_directory,
        )
    except exceptions.Unexpected_character as e:
        Report.error(source_file, e)
        exit(1)
    except exceptions.Fallout as e:
        Report.error_fallout(source_file, e)
        exit(1)
    except Exception as e:
        raise

def assemble_and_link(main_source_file, main_output_file):
    main_dependency_file = '{}.d'.format(os.path.splitext(main_source_file)[0])

    if main_output_file is None:
        main_output_file = '{}.bc'.format(os.path.splitext(main_source_file)[0])

    logs.verbose('main file:            {}'.format(main_source_file))
    logs.verbose('main output file:     {}'.format(main_output_file))
    logs.verbose('main dependency file: {}'.format(main_dependency_file))

    main_imports = []
    with open(main_dependency_file, 'r') as ifstream:
        main_imports = json.loads(ifstream.read())['imports']

    if main_imports:
        prefix = 'imports: '
        logs.verbose('{}{}'.format(prefix, main_imports[0]['module_name']))

        prefix = ' ' * len(prefix)
        for each in main_imports[1:]:
            logs.verbose('{}{}'.format(prefix, each['module_name']))

    import_paths = {}

    for each in main_imports:
        imported_module_name = each['module_name']
        module_source_path = os.path.join(*imported_module_name.split('::')) + '.asm'
        module_binary_path = os.path.join(*imported_module_name.split('::')) + '.module'
        module_ffi_binary_path = os.path.join(*imported_module_name.split('::')) + '.so'

        logs.debug('looking for module {}'.format(imported_module_name))
        for candidate in env.VIUACT_LIBRARY_PATH:
            candidate_module_source_path = os.path.join(candidate, module_source_path)
            candidate_module_binary_path = os.path.join(candidate, module_binary_path)
            candidate_module_ffi_binary_path = os.path.join(candidate, module_ffi_binary_path)

            found_source_form = os.path.isfile(candidate_module_source_path)
            found_binary_form = os.path.isfile(candidate_module_binary_path)
            found_ffi_binary_form = os.path.isfile(candidate_module_ffi_binary_path)

            if not each['foreign']:
                logs.debug('    in {}{}'.format(candidate_module_binary_path, (
                    ' (found)' if found_binary_form else ''
                )))
                if found_binary_form:
                    import_paths[imported_module_name] = candidate_module_binary_path
                    break

                logs.debug('    in {}{}'.format(candidate_module_source_path, (
                    ' (found)' if found_source_form else ''
                )))
                if found_source_form:
                    import_paths[imported_module_name] = candidate_module_source_path
                    break

            if each['foreign']:
                logs.debug('    in {}{}'.format(candidate_module_ffi_binary_path, (
                    ' (found)' if found_ffi_binary_form else ''
                )))
                if found_ffi_binary_form:
                    import_paths[imported_module_name] = candidate_module_ffi_binary_path
                    break

        if imported_module_name not in import_paths:
            sys.stderr.write('error: could not find module {}\n'.format(imported_module_name))
            if not each['foreign']:
                sys.stderr.write('note: put the directory containing module\'s .asm or\n')
                sys.stderr.write('      .module files in VIUACT_OUTPUT_DIRECTORY env variable\n')
            if each['foreign']:
                sys.stderr.write('note: put the directory containing module\'s .so file in\n')
                sys.stderr.write('      VIUACT_LIBRARY_PATH env variable\n')
            exit(1)

    library_files_to_link = []
    for each in main_imports:
        if each['foreign']:
            # If the module is foreign, let's skip it. It should be compiled manually.
            continue

        imported_module_name = each['module_name']

        source_path = import_paths[imported_module_name]
        output_path = '{}.module'.format(os.path.splitext(source_path)[0])

        is_binary_form = source_path.endswith('.module')

        library_files_to_link.append(source_path if is_binary_form else output_path)

        if is_binary_form:
            # The module was found in binary form.
            logs.debug('using binary: {}'.format(source_path))
            continue

        logs.debug('assembling: {} -> {}'.format(source_path, output_path))


        module_hash_path = '{}.hash'.format(os.path.splitext(source_path)[0])
        module_hash_previous = '0'
        if os.path.isfile(module_hash_path):
            with open(module_hash_path, 'r') as ifstream:
                module_hash_previous = ifstream.read().strip()

        module_hash_current = None
        with open(source_path, 'rb') as ifstream:
            module_hash_current = hashlib.sha1(ifstream.read()).hexdigest()

        if module_hash_current == module_hash_previous:
            print('skipping asm: {} -> {} (module has not changed)'.format(
                source_path,
                output_path,
            ))
            continue

        print('running asm:  {} -> {}'.format(source_path, output_path))
        with open(module_hash_path, 'w') as ofstream:
            ofstream.write('{}\n'.format(module_hash_current))

        asm_process_args = (
            env.VIUA_ASM_PATH,
            '-Wunused-register',
        ) + env.VIUACT_ASM_FLAGS + (
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

    module_hash_path = '{}.hash'.format(os.path.splitext(main_source_file)[0])
    module_hash_previous = '0'
    if os.path.isfile(module_hash_path):
        with open(module_hash_path, 'r') as ifstream:
            module_hash_previous = ifstream.read().strip()

    module_hash_current = None
    with open(main_source_file, 'rb') as ifstream:
        module_hash_current = hashlib.sha1(ifstream.read()).hexdigest()

    if (module_hash_current == module_hash_previous) and os.path.isfile(main_output_file):
        print('skipping asm: {} -> {} (module has not changed)'.format(
            main_source_file,
            main_output_file,
        ))
        return

    print('running asm:  {} -> {}'.format(main_source_file, main_output_file))
    with open(module_hash_path, 'w') as ofstream:
        ofstream.write('{}\n'.format(module_hash_current))

    asm_process_args = (
        env.VIUA_ASM_PATH,
        '-Wunused-register',
    ) + env.VIUACT_ASM_FLAGS + (
    ) + (
        ('--verbose',)
        if env.VIUACT_DEBUGGING
        else ()
    ) + (
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
