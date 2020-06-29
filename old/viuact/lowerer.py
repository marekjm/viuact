import json
import os
import sys

from viuact import exceptions, token_types, group_types, lexer, logs, parser, emitter, env


class Visibility_information:
    def __init__(self, prefix, function_prefix = None):
        # In case of top-level scope: None.
        # In case of module scope: name of the module.
        # In any other case: undefined.
        self.prefix = prefix

        # Just in case the visibility is from a nested function.
        self.function_prefix = function_prefix

        # A list of visible module names (strings).
        self.modules = []
        self.nested_modules = {}

        # A dictionary of visible functions. Keys are names, values are
        # arities.
        # Why? Because Viuact does not need arities, but Viua assembly
        # language does, and when you encounter syntax like this:
        #
        #       (let fn f)
        #
        # you need the arity information to produce output like this:
        #
        #       function %fn local f/1
        #
        self.functions = {}

        # List of functions that need to have `.signature:` directive
        # in emitted assembly source code.
        self.signatures = []

        # List of imported modules.
        self.imports = []

        self.enums = {}

    def add_module(self, name):
        if type(name) is Visibility_information:
            self.modules.append(name.prefix)
        elif type(name) is str:
            self.modules.append(name)
        else:
            raise TypeError(name)

    def nest_module(self, module):
        self.nested_modules[module.prefix] = module
        self.add_module(module)

    def add_function(self, name, arity, real_name = None, from_module = None, params = None):
        self.functions[name] = {
            'arity': arity,
            'real_name': (real_name or name),
            'from_module': from_module,
            'params': params,
            'imported': None,
        }

    def insert_function(self, name, value, bytecode_name : str = None):
        self.functions[name] = value

    def import_function(self, name, value):
        value['imported'] = value['from_module']
        self.insert_function(name, value)

    def local_fns(self):
        return list(filter(lambda each: each.get('imported') is None,
            self.functions.values()))

    def real_name(self, name, token):
        if name not in self.functions:
            raise exceptions.No_such_function('no function named: {}()'.format(name), token)
        return (self.functions[name].get('bytecode_name') or self.functions[name]['real_name'])

    def fn_spec(self, name):
        return self.functions[name]

    def add_signature_for(self, name, fn_bytecode_name : str = None):
        self.signatures.append('{name}/{arity}'.format(
            name = (fn_bytecode_name or name),
            arity = self.functions[name]['arity']
        ))

    def nested_in(self, function_name):
        v = Visibility_information(
            prefix = self.prefix,
            function_prefix = ((self.function_prefix or '') + '__' + function_name),
        )
        v.modules = self.modules[:]
        for each in self.functions:
            v.insert_function(
                name = each,
                value = self.functions[each],
            )
        return v

    def add_import(self, module_name, real_name : str = None, foreign = False):
        self.imports.append({
            'module_name': module_name,
            'real_name': (module_name if (real_name is None) else real_name),
            'foreign': foreign,
        })

    def add_enum(self, name, values, real_name = None, from_module = None):
        self.enums[name] = {
            'values': values,
            'real_name': (real_name or name),
            'from_module': from_module,
            'is_tag_enum': any(each['tag'] for each in values.values()),
        }

    def insert_enum(self, name, value):
        self.enums[name] = value


def make_meta(name):
    return Visibility_information(name)


def parse_interface_file(source):
    return json.loads(source)

def perform_imports(import_expressions, meta):
    if not import_expressions:
        return

    import_expressions = list(import_expressions)
    for spec in import_expressions:
        mod_name = spec.to_string()

        # First, look into our nested modules. Maybe we are even importing an
        # inline module in which case we already have it parsed and ready.
        if mod_name in meta.nested_modules:
            for each in meta.nested_modules[mod_name].functions.values():
                meta.import_function(
                    name = each['real_name'],
                    value = each,
                )
                meta.add_signature_for(each['real_name'])

            for enum_name, enum_meta in meta.nested_modules[mod_name].enums.items():
                if enum_meta['from_module'] == mod_name:
                    meta.insert_enum(
                        name = enum_meta['real_name'],
                        value = enum_meta,
                    )

            meta.add_import(mod_name)
            continue

        # If the module is not our nested module, we have to look for its
        # interface file. Search the library path until we find a suitable file.
        found = False
        for library_dir in env.VIUACT_LIBRARY_PATH:
            logs.debug('checking {} for module {}'.format(library_dir, mod_name))

            mod_interface_path = os.path.join(library_dir, *mod_name.split('::')) + '.i'
            logs.debug('    candidate {}'.format(mod_interface_path))
            if os.path.isfile(mod_interface_path):
                logs.debug('    found {}'.format(mod_interface_path))
                found = True
                with open(mod_interface_path, 'r') as ifstream:
                    interface = parse_interface_file(ifstream.read())
                    for each in interface['fns']:
                        if each['from_module'] == mod_name:
                            # Optional. Name of the function as seen in the bytecode
                            # module. Useful for foreign modules for which the
                            # interface is written manually, but must still agree with the
                            # naming convention used by Viuact.
                            fn_bytecode_name = each.get('bytecode_name')

                            # Full name of the function; the name base name of the
                            # function prefixed by the full name of the module in which it
                            # is contained.
                            fn_full_name = each['real_name']

                            if 'params' not in each:
                                raise Exception('interface for {}() does include "params"'.format(
                                    fn_full_name.replace('::', '.'),
                                ))

                            if each['arity'] != len(each['params']):
                                s = 'interface for {}() has mismatched arity and parameters count: {} != {}'
                                raise Exception(s.format(
                                    fn_full_name.replace('::', '.'),
                                    each['arity'],
                                    len(each['params']),
                                ))

                            L = token_types.Labeled_parameter_name
                            N = token_types.Name
                            each['params'] = [
                                (L(p) if p.startswith('~') else N(p))
                                for p
                                in each['params']
                            ]

                            meta.import_function(
                                name = fn_full_name,
                                value = each,
                            )
                            meta.add_signature_for(fn_full_name, fn_bytecode_name)

                    if 'enums' not in interface:
                        logs.warn('module {} (found in {}) does not define "enums"'.format(
                            mod_name,
                            library_dir,
                        ))
                    for each in interface.get('enums', []):
                        meta.insert_enum(
                            name = each['real_name'],
                            value = each,
                        )

                    meta.add_import(
                        module_name = mod_name,
                        real_name = interface['real_name'],
                        foreign = interface['foreign'],
                    )
                break

        if found:
            continue

        raise exceptions.No_such_module('no such module: {}'.format(mod_name), spec)


def lower_file(expressions, module_prefix, compilation_filesystem_root):
    lowered_function_bodies = []

    meta = make_meta(name = module_prefix)

    for each in expressions:
        if type(each) not in (group_types.Inline_module, group_types.Module,):
            continue

        bodies, mod_meta = lower_module(
            module_expr = each,
            in_module = (),
            compilation_filesystem_root = compilation_filesystem_root,
        )
        lowered_function_bodies.extend(bodies)

        for each in mod_meta.nested_modules.values():
            meta.nest_module(each)
        meta.nest_module(mod_meta)

    perform_imports(
        import_expressions = filter(lambda each: type(each) is group_types.Import, expressions),
        meta = meta,
    )

    for each in expressions:
        if type(each) is not group_types.Enum_definition:
            continue

        enum_name = str(each.name.token)
        enum_values = each.elements_spec()
        meta.add_enum(
            name = enum_name,
            values = enum_values,
            from_module = module_prefix,
        )

    for each in expressions:
        if type(each) is not group_types.Function:
            continue
        meta.add_function(
            name = str(each.name.token),
            arity = len(each.arguments),
            from_module = module_prefix,
            params = each.arguments,
        )

    for each in expressions:
        if type(each) is not group_types.Function:
            continue
        lowered_function_bodies.extend(lower_function(each, meta = meta))

    return lowered_function_bodies, meta


def lower_module_impl(module_expr, in_module, compilation_filesystem_root):
    lowered_function_bodies = []

    base_mod_name = str(module_expr.name.token)
    full_mod_name = in_module + (base_mod_name,)

    meta = make_meta(name = '::'.join(full_mod_name))

    for mod_name in module_expr.module_names:
        mod_def = module_expr.modules[mod_name]
        mod_bodies, mod_meta = lower_module(
            module_expr = mod_def,
            in_module = full_mod_name,
            compilation_filesystem_root = compilation_filesystem_root,
        )
        lowered_function_bodies.extend(mod_bodies)

        for each in mod_meta.nested_modules.values():
            meta.nest_module(each)
        meta.nest_module(mod_meta)

    perform_imports(
        import_expressions = module_expr.imports,
        meta = meta,
    )

    for each in module_expr.enums:
        if type(each) is not group_types.Enum_definition:
            continue

        enum_name = str(each.name.token)
        enum_values = each.elements_spec()

        module_prefix = '::'.join(full_mod_name)
        real_name = '{}::{}'.format(module_prefix, enum_name)
        meta.add_enum(
            name = enum_name,
            values = enum_values,
            real_name = real_name,
            from_module = module_prefix,
        )

    for fn_name in module_expr.function_names:
        real_name = '{}::{}'.format('::'.join(full_mod_name), fn_name)
        meta.add_function(
            name = fn_name,
            arity = len(module_expr.functions[fn_name].arguments),
            real_name = real_name,
            from_module = '::'.join(full_mod_name),
            params = module_expr.functions[fn_name].arguments,
        )

    for fn_name in module_expr.function_names:
        fn_def = module_expr.functions[fn_name]

        real_name = '{}::{}'.format('::'.join(full_mod_name), fn_name)
        lowered_function_bodies.extend(lower_function(
            fn_def,
            in_module = full_mod_name,
            meta = meta,
        ))
        meta.add_function(
            name = fn_name,
            arity = len(fn_def.arguments),
            real_name = real_name,
            from_module = '::'.join(full_mod_name),
            params = fn_def.arguments,
        )

    return lowered_function_bodies, meta

def load_as_inline_module(source, base_mod_name):
    tokens = lexer.strip_comments(lexer.lex(source))
    expressions = parser.parse(parser.group(tokens))

    module = group_types.Inline_module(name = token_types.Module_name(base_mod_name))
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

    return module

def lower_module(module_expr, in_module, compilation_filesystem_root):
    if type(module_expr) is group_types.Inline_module:
        return lower_module_impl(module_expr, in_module, compilation_filesystem_root)

    base_mod_name = str(module_expr.name.token)
    full_mod_name = in_module + (base_mod_name,)
    mod_path = os.path.join(compilation_filesystem_root, *in_module, '{}.lisp'.format(base_mod_name))

    with open(mod_path, 'r') as ifstream:
        module = load_as_inline_module(
            source = ifstream.read(),
            base_mod_name = base_mod_name,
        )
        return lower_module_impl(
            module_expr = module,
            in_module = in_module,
            compilation_filesystem_root = compilation_filesystem_root,
        )

def lower_function_body(body):
    instructions = [
        body[0].to_string(),   # signature
    ]

    for each in body[1:-1]:
        instructions.append('    {}'.format(
            each.to_string(),
        ))

    instructions.append(body[-1].to_string())  # .end

    return '\n'.join(instructions)

def output_function_body(fn, in_module, meta):
    full_fn_name = in_module + (str(fn.name.token),)

    inner_body = []
    state = emitter.State(
        function_name = '::'.join(full_fn_name),
        upper = None,
        visible_fns = meta,
    )

    for i, each in enumerate(fn.arguments):
        source = emitter.Slot(
            None,
            i,
            emitter.PARAMETERS_REGISTER_SET,
        )
        parameter_label = (
            str(each.token)[1:]
            if type(each) is token_types.Labeled_parameter_name
            else str(each.token))
        dest = state.get_slot(parameter_label)
        inner_body.append(emitter.Verbatim('; parameter {}'.format(
            str(each.token),
        )))
        inner_body.append(emitter.Move.make_move(
            source,
            dest,
        ))
    if fn.arguments:
        inner_body.append(emitter.Verbatim(''))

    allocated_return_slot = None
    body_type = type(fn.body)
    if body_type == group_types.Name_ref:
        pass
    else:
        allocated_return_slot = state.get_slot(name = None, anonymous = True)

    state.get_slot(name = None, anonymous = True)
    return_slot = emitter.emit_expr(
        body = inner_body,
        expr = fn.body,
        state = state,
        meta = meta,
        slot = allocated_return_slot,
        toplevel = False,
    )

    body = [
        emitter.Verbatim('.function: {}/{}'.format(
            state.function_name,
            len(fn.arguments),
        )),
    ]

    if True:
        actual_pressure = state.next_slot[emitter.LOCAL_REGISTER_SET]
        static_pressure = state.register_pressure[emitter.LOCAL_REGISTER_SET]
        if actual_pressure < static_pressure:
            fmt = '; local register pressure = {} (actually used {})'
            body.append(emitter.Verbatim(fmt.format(
                static_pressure,
                actual_pressure,
            )))

            fmt = '; actual pressure is {:.4f}% of static pressure'
            body.append(emitter.Verbatim(fmt.format(
                ((actual_pressure / static_pressure) * 100),
            )))

            body.append(emitter.Verbatim('; saved {} local register(s)'.format(
                (static_pressure - actual_pressure),
            )))
        else:
            fmt = '; local register pressure = {} (actually used {})'
            body.append(emitter.Verbatim(fmt.format(
                static_pressure,
                actual_pressure,
            )))

    body.append(emitter.Verbatim('allocate_registers %{} local'.format(
        state.next_slot[emitter.LOCAL_REGISTER_SET],
    )))
    body.append(emitter.Verbatim(''))
    body.extend(inner_body)
    if type(inner_body[-1]) is emitter.Call and inner_body[-1].kind == emitter.Call.Kind.Tail:
        pass    # We don't have to return anything for tail calls as they will
                # replace our call frame anyway.
    else:
        body.append(emitter.Verbatim(''))
        body.append(emitter.Verbatim('; set return value'))
        body.append(emitter.Move.make_move(
            return_slot,
            emitter.Slot(None, 0,)
        ))
        body.append(emitter.Verbatim('return'))
    body.append(emitter.Verbatim('.end'))
    return state.nested_fns + [('::'.join(full_fn_name), body,)]

def lower_function(fn_expr, meta, in_module = ()):
    # Bodies instead of a single body, because a function may contain
    # nested functions and thus compile to multiple bodies.
    try:
        bodies = output_function_body(fn_expr, in_module, meta)
        return [(name, lower_function_body(each),) for (name, each) in bodies]
    except Exception:
        print('while lowering function {}:'.format(fn_expr.to_string()))
        raise
