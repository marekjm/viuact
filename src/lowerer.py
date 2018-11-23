import json

import exceptions
import group_types
import emitter


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
            raise exceptions.No_such_function('no function named', token)
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


def lower_file(expressions, module_prefix):
    lowered_function_bodies = []

    meta = make_meta(name = module_prefix)

    for each in expressions:
        if type(each) is group_types.Module:
            bodies, mod_meta = lower_module(each)
            lowered_function_bodies.extend(bodies)

            meta.add_module(mod_meta)
            for each in mod_meta.functions:
                meta.insert_function(
                    name = '{}::{}'.format(mod_meta.prefix, each),
                    value = mod_meta.functions[each],
                )

    print('x-file-level: modules:  ', meta.modules)
    print('x-file-level: functions:', meta.functions)

    for each in expressions:
        if type(each) is group_types.Function:
            meta.add_function(
                name = str(each.name.token),
                arity = len(each.arguments),
                from_module = module_prefix,
            )
            lowered_function_bodies.extend(lower_function(each, meta = meta))

    print('file-level: modules:  ', meta.modules)
    print('file-level: functions:', meta.functions)

    return lowered_function_bodies, meta


def lower_module(module_expr, in_module = ()):
    lowered_function_bodies = []

    base_mod_name = str(module_expr.name.token)
    full_mod_name = in_module + (base_mod_name,)

    meta = make_meta(name = '::'.join(full_mod_name))

    for mod_name in module_expr.module_names:
        mod_def = module_expr.modules[mod_name]
        mod_bodies, mod_meta = lower_module(
            mod_def,
            in_module = full_mod_name,
        )
        lowered_function_bodies.extend(mod_bodies)

        meta.add_module(mod_meta)
        for fn_name, fn_value in mod_meta.functions.items():
            meta.insert_function(
                name = fn_name,
                value = fn_value,
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

    print('module-level: {}: modules:  '.format(meta.prefix), meta.modules)
    print('module-level: {}: functions:'.format(meta.prefix), meta.functions)

    return lowered_function_bodies, meta


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
