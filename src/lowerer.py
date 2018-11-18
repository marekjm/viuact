import json

import group_types
import emitter


def make_meta(name = None):
    return {
        'name': name,
        'modules': {
        },
        'functions': [],
    }


def lower_file(expressions):
    lowered_function_bodies = []

    meta = make_meta()

    for each in expressions:
        if type(each) is group_types.Module:
            bodies, mod_meta = lower_module(each, upper_meta = meta)
            lowered_function_bodies.extend(bodies)
            meta['modules'][str(each.name.token)] = mod_meta

    for each in expressions:
        if type(each) is group_types.Function:
            lowered_function_bodies.append(lower_function(each, upper_meta = meta))

    flat_meta = {
        'functions': [],
    }
    for each in meta['modules'].values():
        for fn in each['functions']:
            flat_meta['functions'].append(fn)
    for each in meta['functions']:
        flat_meta['functions'].append(each)

    print(json.dumps(flat_meta, indent = 2))
    return lowered_function_bodies, flat_meta


def lower_module(module_expr, upper_meta, in_module = ()):
    lowered_function_bodies = []

    full_mod_name = in_module + (str(module_expr.name.token),)

    meta = make_meta()

    for mod_name in module_expr.module_names:
        mod_def = module_expr.modules[mod_name]
        mod_bodies, mod_meta = lower_module(
            mod_def,
            in_module = full_mod_name,
            upper_meta = meta,
        )
        lowered_function_bodies.extend(mod_bodies)

        meta['modules'][mod_name] = mod_meta
        for each in mod_meta['modules'].values():
            for fn in each['functions']:
                meta['functions'].append('{}::{}'.format(
                    each['name'],
                    fn,
                ))

    for fn_name in module_expr.function_names:
        fn_def = module_expr.functions[fn_name]
        lowered_function_bodies.append(lower_function(
            fn_def,
            in_module = full_mod_name,
            upper_meta = meta,
        ))
        meta['functions'].append(fn_name)

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
    return body

def lower_function(fn_expr, upper_meta, in_module = ()):
    body = output_function_body(fn_expr, in_module, upper_meta)
    return lower_function_body(body)
