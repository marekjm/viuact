import json
import os
import sys

import exceptions
import token_types
import group_types
import lexer
import parser
import emitter
import env


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

    def add_module(self, name):
        if type(name) is Visibility_information:
            self.modules.append(name.prefix)
        elif type(name) is str:
            self.modules.append(name)
        else:
            raise TypeError(name)

    def add_function(self, name, arity, real_name = None, from_module = None):
        self.functions[name] = {
            'arity': arity,
            'real_name': (real_name or name),
            'from_module': from_module,
        }

    def insert_function(self, name, value):
        self.functions[name] = value

    def real_name(self, name, token):
        if name not in self.functions:
            raise exceptions.No_such_function('no function named: {}()'.format(name), token)
        return self.functions[name]['real_name']

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


def make_meta(name):
    return Visibility_information(name)


def parse_interface_file(source):
    return json.loads(source)

def perform_imports(import_expressions, meta):
    for spec in import_expressions:
        mod_name = spec.to_string()

        if mod_name in meta.modules:
            for _, each in list(meta.functions.items()):
                if each['from_module'] == mod_name:
                    meta.insert_function(
                        name = each['real_name'],
                        value = each,
                    )
            continue

        found = False
        for each in env.VIUAC_LIBRARY_PATH:
            print('checking {} for module {}'.format(each, mod_name))

            mod_interface_path = os.path.join(each, *mod_name.split('.')) + '.i'
            if os.path.isfile(mod_interface_path):
                print('    found {}'.format(mod_interface_path))
                found = True
                with open(mod_interface_path, 'r') as ifstream:
                    interface = parse_interface_file(ifstream.read())
                    for each in interface['fns']:
                        if each['from_module'] == mod_name:
                            meta.insert_function(
                                name = each['real_name'],
                                value = each,
                            )
                break

        if found:
            continue

        sys.stderr.write('warning: available modules: {}\n'.format(', '.join(meta.modules)))
        raise exceptions.No_such_module('no such module: {}'.format(mod_name), spec)


def lower_file(expressions, module_prefix, compilation_filesystem_root):
    lowered_function_bodies = []

    meta = make_meta(name = module_prefix)

    for each in expressions:
        if type(each) is group_types.Inline_module:
            bodies, mod_meta = lower_module(
                module_expr = each,
                in_module = (),
                compilation_filesystem_root = compilation_filesystem_root,
            )
            lowered_function_bodies.extend(bodies)

        for each in mod_meta.modules:
            meta.add_module(each)
        meta.add_module(mod_meta)
        for fn_name, fn_value in mod_meta.functions.items():
            meta.insert_function(
                name = fn_name,
                value = fn_value,
            )

    perform_imports(
        import_expressions = filter(lambda each: type(each) is group_types.Import, expressions),
        meta = meta,
    )

    # print('x-file-level: modules:  ', meta.modules)
    # print('x-file-level: functions:', meta.functions)

    for each in expressions:
        if type(each) is group_types.Function:
            meta.add_function(
                name = str(each.name.token),
                arity = len(each.arguments),
                from_module = module_prefix,
            )
            lowered_function_bodies.extend(lower_function(each, meta = meta))

    # print('file-level: modules:  ', meta.modules)
    # print('file-level: functions:', meta.functions)

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

        for each in mod_meta.modules:
            meta.add_module(each)
        meta.add_module(mod_meta)
        for fn_name, fn_value in mod_meta.functions.items():
            meta.insert_function(
                name = fn_name,
                value = fn_value,
            )

    perform_imports(
        import_expressions = module_expr.imports,
        meta = meta,
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
        )

    # print('module-level: {}: modules:  '.format(meta.prefix), meta.modules)
    # print('module-level: {}: functions:'.format(meta.prefix), meta.functions)

    return lowered_function_bodies, meta

def lower_module(module_expr, in_module, compilation_filesystem_root):
    if type(module_expr) is group_types.Inline_module:
        return lower_module_impl(module_expr, in_module, compilation_filesystem_root)

    base_mod_name = str(module_expr.name.token)
    full_mod_name = in_module + (base_mod_name,)
    mod_path = os.path.join(compilation_filesystem_root, *in_module, '{}.lisp'.format(base_mod_name))

    with open(mod_path, 'r') as ifstream:
        tokens = lexer.strip_comments(lexer.lex(ifstream.read()))
        expressions = parser.parse(parser.group(tokens))

        module = group_types.Inline_module(name = token_types.Module_name(base_mod_name))
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
        dest = state.get_slot(
            str(each.token),
        )
        inner_body.append(emitter.Move.make_move(
            source,
            dest,
        ))
    if fn.arguments:
        inner_body.append(emitter.Verbatim(''))

    for each in fn.body:
        # Expressions evaluated at function-level are given anonymous
        # slots.
        # Why? Because they are not assigned to anything. If an
        # expression is assigned to an anonymous slot it can decide for
        # itself what to do with this situation; function calls will
        # return to void, literals and let-bindings will be created.
        emitter.emit_expr(
            body = inner_body,
            expr = each,
            state = state,
            meta = meta,
        )
        inner_body.append(emitter.Verbatim(''))

    body = [
        emitter.Verbatim('.function: {}/{}'.format(
            state.function_name,
            len(fn.arguments),
        )),
    ]
    body.append(emitter.Verbatim('allocate_registers %{} local'.format(
        state.next_slot[emitter.LOCAL_REGISTER_SET],
    )))
    body.append(emitter.Verbatim(''))
    body.extend(inner_body)
    body.append(emitter.Move.make_move(
        state.last_used_slot,
        emitter.Slot(None, 0,)
    ))
    body.append(emitter.Verbatim('return'))
    body.append(emitter.Verbatim('.end'))
    return state.nested_fns + [('::'.join(full_fn_name), body,)]

def lower_function(fn_expr, meta, in_module = ()):
    # Bodies instead of a single body, because a function may contain
    # nested functions and thus compile to multiple bodies.
    bodies = output_function_body(fn_expr, in_module, meta)
    return [(name, lower_function_body(each),) for (name, each) in bodies]
