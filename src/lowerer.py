import emitter


def lower_module(module_expr, in_module = None):
    lowered_function_bodies = []

    for fn_name, fn_def in module_expr.functions.items():
        body = output_function_body(fn_def)
        s = lower_function_body(body)
        lowered_function_bodies.append(s)

    return lowered_function_bodies


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

def output_function_body(fn):
    body = [
        emitter.Verbatim('.function: {}/{}'.format(
            str(fn.name.token),
            len(fn.arguments),
        )),
    ]

    inner_body = []
    state = emitter.State()

    for i, each in enumerate(fn.arguments):
        source = emitter.Slot(
            None,
            i,
            'parameters',
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

def lower_function(fn_expr, in_module = None):
    body = output_function_body(fn_expr)
    return lower_function_body(body)
