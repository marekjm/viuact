import json

import group_types
import emitter


class Visibility_information:
    def __init__(self, prefix):
        # In case of top-level scope: None.
        # In case of module scope: name of the module.
        # In any other case: undefined.
        self.prefix = prefix

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

    def add_function(self, name, arity):
        self.functions[name] = arity


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
                meta.add_function('{}.{}'.format(mod_meta.prefix, each), mod_meta.functions[each])

    for each in expressions:
        if type(each) is group_types.Function:
            meta.add_function(str(each.name.token), len(each.arguments))
            lowered_function_bodies.extend(lower_function(each, upper_meta = meta))

    print('file-level: modules:  ', meta.modules)
    print('file-level: functions:', meta.functions)

    return lowered_function_bodies, meta


def lower_module(module_expr, in_module = ()):
    lowered_function_bodies = []

    full_mod_name = in_module + (str(module_expr.name.token),)

    meta = make_meta(name = '.'.join(full_mod_name))

    for mod_name in module_expr.module_names:
        mod_def = module_expr.modules[mod_name]
        mod_bodies, mod_meta = lower_module(
            mod_def,
            in_module = full_mod_name,
            upper_meta = meta,
        )
        lowered_function_bodies.extend(mod_bodies)

        # meta['modules'][mod_name] = mod_meta
        # for each in mod_meta['modules'].values():
        #     for fn in each['functions']:
        #         meta['functions'].append('{}::{}'.format(
        #             each['name'],
        #             fn,
        #         ))

    for fn_name in module_expr.function_names:
        fn_def = module_expr.functions[fn_name]
        lowered_function_bodies.extend(lower_function(
            fn_def,
            in_module = full_mod_name,
            upper_meta = meta,
        ))
        meta.add_function(fn_name, len(fn_def.arguments))

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

def output_function_body(fn, in_module, upper_meta):
    full_fn_name = in_module + (str(fn.name.token),)
    body = [
        emitter.Verbatim('.function: {}/{}'.format(
            '::'.join(full_fn_name),
            len(fn.arguments),
        )),
    ]

    inner_body = []
    state = emitter.State()

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
            meta = upper_meta,
        )
        inner_body.append(emitter.Verbatim(''))

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
    return state.nested_fns + [body]

def lower_function(fn_expr, upper_meta, in_module = ()):
    # Bodies instead of a single body, because a function may contain
    # nested functions and thus compile to multiple bodies.
    bodies = output_function_body(fn_expr, in_module, upper_meta)
    return [lower_function_body(each) for each in bodies]
