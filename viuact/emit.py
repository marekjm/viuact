import hashlib

import viuact.forms
from viuact.ops import (
    Register_set,
    Call,
    Ctor,
    Move,
    Print,
    Slot,
    Verbatim,
)


BUILTIN_FUNCTIONS = (
    'print',
)


class Type:
    class Int(viuact.typesystem.t.Value):
        SIGNED_INTEGER_TYPES = (
            'i8',
            'i16',
            'i32',
            'i64',
        )
        UNSIGNED_INTEGER_TYPES = (
            'u8',
            'u16',
            'u32',
            'u64',
        )
        INTEGER_TYPES = (SIGNED_INTEGER_TYPES + UNSIGNED_INTEGER_TYPES)

        def cast_from(self, t):
            if t.to_string() not in Type.Int.INTEGER_TYPES:
                return False

            # Integers should be classified according to:
            #
            #   - signedness: signed and unsigned
            #   - bit width: 1, 4, 8, 16, 32, 64
            #   - endiannes: host, little, and big
            #   - overflow behaviour: wraparound, trap, saturate
            #
            # For example, a UNIX socket port could be represented using an
            # unsigned, 16-bit, big-endian, trapping integer.
            #
            # A PID counter could be represented using an unsigned, 64-bit,
            # host-endian, wraparound integer.
            this_t = self.to_string()
            that_t = t.to_string()
            same_subtype = lambda prefix: (this_t.startswith(prefix) ==
                    that_t.startswith(prefix))
            if not same_subtype('i'):
                return False

            bitwidth_this = int(self.to_string()[1:])
            bitwidth_that = int(self.to_string()[1:])
            return (bitwidth_this >= bitwidth_that)

        @staticmethod
        def is_integer_type(t):
            tt = (I(viuact.typesystem.t.Value) | t)
            return (tt.to_string() in Type.Int.INTEGER_TYPES)

    def string():
        return viuact.typesystem.t.Value(
            name = 'string',
        )

    def i8():
        return Type.Int(
            name = 'i8',
        )

    def i16():
        return Type.Int(
            name = 'i16',
        )

    def i32():
        return Type.Int(
            name = 'i32',
        )

    def i64():
        return Type.Int(
            name = 'i64',
        )

    def u8():
        return Type.Int(
            name = 'u8',
        )

    def u16():
        return Type.Int(
            name = 'u16',
        )

    def u32():
        return Type.Int(
            name = 'u32',
        )

    def u64():
        return Type.Int(
            name = 'u64',
        )

    def bool():
        return viuact.typesystem.t.Value(
            name = 'bool',
        )

    def atom():
        return viuact.typesystem.t.Value(
            name = 'atom',
        )

def typeof(value):
    return str(type(value))[8:-2]


def emit_builtin_call(mod, body, st, result, form):
    if str(form.to().name()) == 'print':
        if len(form.arguments()) != 1:
            raise viuact.errors.Invalid_arity(
                form.to().name().tok().at(),
                expected = 1,
                got = len(form.arguments()),
            )
        with st.scoped() as sc:
            slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = (
                    sc.get_disposable_slot().inhibit_dereference(result.inhibit_dereference())
                    if result.is_void()
                    else result
                ),
                expr = form.arguments()[0],
            )
            arg_t = sc.type_of(slot)
            if arg_t == viuact.typesystem.t.Void():
                raise viuact.errors.Read_of_void(
                    pos = form.arguments()[0].first_token().at(),
                    by = 'print function',
                )

            # st.store(slot.to_string(), Type.void())

            is_pointer = (type(arg_t) is viuact.typesystem.t.Pointer)
            dereference_freely = (not slot.inhibit_dereference())
            deref = (is_pointer and dereference_freely)
            body.append(Print(slot.as_pointer(deref), Print.PRINT))
            body.append(Verbatim(''))

        return slot

def emit_indirect_fn_call(mod, body, st, result, form):
    name = str(form.to().name())
    fn_slot = st.slot_of(name)
    fn_t = st.type_of(fn_slot)

    if len(fn_t.parameter_types()) != len(form.arguments()):
        e = viuact.errors.Invalid_arity(
            form.to().name().tok().at(),
            'from variable {}'.format(name),
        ).note('expected {} argument(s), got {}'.format(
            len(fn_t.parameters()),
            len(form.arguments()),
        ))
        raise e

    body.append(Verbatim('frame %{} arguments'.format(len(form.arguments()))))

    parameter_types = fn_t.parameter_types()
    args = form.arguments()
    for i, arg in enumerate(args):
        body.append(Verbatim('; for argument {}'.format(i)))
        arg_slot = st.get_slot(name = None)
        with st.scoped() as sc:
            slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = arg_slot,
                expr = arg,
            )
            body.append(Move.make_move(
                source = arg_slot,
                dest = Slot(
                    name = None,
                    index = i,
                    register_set = Register_set.ARGUMENTS,
                ),
            ))

            param_t = parameter_types[i]
            arg_t = st.type_of(arg_slot)

            try:
                st.unify_types(param_t, arg_t)
            except viuact.typesystem.state.Cannot_unify:
                raise viuact.errors.Bad_argument_type(
                    arg.first_token().at(),
                    name,
                    (i + 1),
                    st._types.stringify_type(param_t, human_readable = True),
                    st._types.stringify_type(arg_t, human_readable = True),
                )

            # FIXME Maybe mark the slot as moved in some way to aid with error
            # reporting?
            sc.deallocate_slot(arg_slot)

    return_t = fn_t.return_type()

    # Only set type of the result is not a void register (it does not make sense
    # to assign type to a void).
    if not result.is_void():
        st.type_of(result, return_t)

    body.append(Call(
        to = fn_slot.to_string(),
        slot = result,
        kind = Call.Kind.Synchronous,
    ))
    body.append(Verbatim(''))

    return result

def get_fn_candidates(form, mod):
    viuact.util.log.raw('fn candidates for: {} ({})'.format(
        form.to(),
        typeof(form.to()),
    ))

    basic_name = (
           (type(form.to()) is viuact.lexemes.Name)
        or (type(form.to()) is viuact.forms.Name_ref)
    )
    if basic_name:
        base_name = str(form.to().name().tok())
        called_fn_name = '{name}/{arity}'.format(
            name = base_name,
            arity = len(form.arguments()),
        )

        candidates = list(filter(
            lambda each: (each.split('/')[0] == base_name),
            mod.signatures(),
        ))
        if not candidates:
            raise viuact.errors.Unknown_function(
                form.to().name().tok().at(),
                called_fn_name,
            )

        candidates = list(map(lambda each: mod.signature(each), candidates))

        viuact.util.log.raw('candidates: {}'.format(candidates))
        return candidates, mod, called_fn_name, called_fn_name

    if type(form.to()) is viuact.forms.Name_path:
        called_mod_path = '::'.join(map(str, form.to().mod()))
        viuact.util.log.raw('called mod path = {}'.format(called_mod_path))

        called_mod = mod.imported(called_mod_path)
        viuact.util.log.raw('called mod = {}'.format(called_mod))

        base_name = str(form.to().name().tok())
        called_fn_name = '{name}/{arity}'.format(
            name = base_name,
            arity = len(form.arguments()),
        )

        viuact.util.log.raw('x', called_fn_name)
        viuact.util.log.raw('y', list(map(type, called_mod.signatures())))
        candidates = list(filter(
            lambda each: (each.split('/')[0] == base_name),
            called_mod.signatures(),
        ))
        viuact.util.log.raw('z', candidates)
        if not candidates:
            raise viuact.errors.Unknown_function(
                form.to().name().tok().at(),
                called_fn_name,
            )

        candidates = list(map(lambda each: called_mod.signature(each), candidates))

        return candidates, called_mod, called_fn_name, '{}::{}'.format(
            called_mod_path,
            called_fn_name,
        )

    raise None

def emit_direct_fn_call(mod, body, st, result, form):
    if str(form.to().name()) in BUILTIN_FUNCTIONS:
        return emit_builtin_call(mod, body, st, result, form)

    candidates, called_mod, called_fn_name, full_name = get_fn_candidates(form, mod)

    signature = (lambda x: (x[0] if x else None))(list(filter(
        lambda each: each['arity'] == len(form.arguments()),
        candidates
    )))
    if signature is None:
        e = viuact.errors.Invalid_arity(
            form.to().name().tok().at(),
            called_fn_name,
        )
        for each in candidates:
            e.note('candidate: {}({})'.format(
                each[1]['base_name'],
                ' '.join(map(lambda p: str(p.name()), each[1]['parameters'])),
            ))
        raise e

    type_signature = called_mod.signature(called_fn_name)
    if (called_mod.name() == mod.name()) and not mod.is_fn_defined(called_fn_name):
        raise viuact.errors.Call_to_undefined_function(
            form.to().name().tok().at(),
            called_fn_name,
        )

    args = []
    if True:
        parameters = signature['parameters']
        arguments = form.arguments()

        need_labelled = list(filter(
            lambda a: type(a) is viuact.forms.Labelled_parameter,
            parameters))
        need_positional = list(filter(
            lambda a: type(a) is viuact.forms.Named_parameter, parameters))

        got_labelled = dict(
            map(lambda a: ( str(a.name()), a.val(), ),
            filter(lambda a: type(a) is viuact.forms.Argument_bind,
            arguments)))
        got_positional = list(filter(
            lambda a: type(a) is not viuact.forms.Argument_bind, arguments))

        # print('positional:', need_positional, '=>', got_positional)
        # print('labelled:',
        #     list(map(lambda a: str(a.name()), need_labelled)),
        #     '=>', got_labelled)

        if len(got_positional) < len(need_positional):
            raise viuact.errors.Missing_positional_argument(
                form.to().name().tok().at(),
                called_fn_name,
                need_positional[len(got_positional)],
            )
        for l in need_labelled:
            if str(l.name()) not in got_labelled:
                raise viuact.errors.Missing_labelled_argument(
                    form.to().name().tok().at(),
                    called_fn_name,
                    l,
                )

        args = got_positional[:]
        for a in need_labelled:
            args.append(got_labelled[str(a.name())])

    body.append(Verbatim('frame %{} arguments'.format(len(form.arguments()))))

    parameter_types = []
    tmp = {}
    for each in type_signature['template_parameters']:
        tmp[viuact.typesystem.t.Template(each.name()[1:])] = st.register_template_variable(each)
    for each in type_signature['parameters']:
        if type(each) is viuact.typesystem.t.Value:
            parameter_types.append(each.concretise(tmp))
        elif type(each) is viuact.typesystem.t.Fn:
            parameter_types.append(each.concretise(tmp))
        else:
            raise None

    for i, arg in enumerate(args):
        body.append(Verbatim('; for argument {}'.format(i)))
        slot = st.get_slot(name = None)
        with st.scoped() as sc:
            slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = slot,
                expr = arg,
            )
            body.append(Move.make_move(
                source = slot,
                dest = Slot(
                    name = None,
                    index = i,
                    register_set = Register_set.ARGUMENTS,
                ),
            ))

            param_t = parameter_types[i]
            arg_t = st.type_of(slot)

            try:
                st.unify_types(param_t, arg_t)
            except viuact.typesystem.state.Cannot_unify:
                raise viuact.errors.Bad_argument_type(
                    arg.first_token().at(),
                    called_fn_name,
                    (i + 1),
                    st._types.stringify_type(param_t, human_readable = True),
                    st._types.stringify_type(arg_t, human_readable = True),
                )

            # FIXME Maybe mark the slot as moved in some way to aid with error
            # reporting?
            sc.deallocate_slot(slot)

    return_t = type_signature['return'].concretise(tmp)

    # Only set type of the result is not a void register (it does not make sense
    # to assign type to a void).
    if not result.is_void():
        st.type_of(result, return_t)

    body.append(Call(
        to = full_name,
        slot = result,
        kind = Call.Kind.Synchronous,
    ))
    body.append(Verbatim(''))

    return result

def emit_fn_call(mod, body, st, result, form):
    if str(form.to().name()) in BUILTIN_FUNCTIONS:
        return emit_builtin_call(mod, body, st, result, form)

    base_name = str(form.to().name().tok())
    try:
        # Let's see if the base name is a name of a slot. If that is the case
        # this is an indirect call and we have to employ slightly different
        # machinery to emit it, than what would be used for direct calls.
        st.slot_of(base_name)
        return emit_indirect_fn_call(mod, body, st, result, form)
    except KeyError:
        pass

    return emit_direct_fn_call(mod, body, st, result, form)

def emit_operator_concat(mod, body, st, result, expr):
    if len(expr.arguments()) < 2:
        raise viuact.errors.Invalid_arity(
            pos = expr.operator().tok().at(),
            s = str(expr.operator()),
            kind = viuact.errors.Invalid_arity.OPERATOR,
        ).note('expected at least 2 arguments, got {}'.format(
            len(expr.arguments()),
        ))

    with st.scoped() as sc:
        lhs_slot = sc.get_slot(None)
        rhs_slot = sc.get_slot(None)

        args = expr.arguments()

        lhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = lhs_slot,
            expr = args[0],
        )
        rhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = rhs_slot,
            expr = args[1],
        )
        arg_t = sc.type_of(rhs_slot)
        if arg_t.to_string() != Type.string().to_string():
            is_pointer = (type(arg_t) is viuact.typesystem.t.Pointer)
            dereference_freely = (not rhs_slot.inhibit_dereference())
            deref = (is_pointer and dereference_freely)
            body.append(Verbatim('text {} {}'.format(
                rhs_slot.to_string(),
                rhs_slot.as_pointer(deref).to_string(),
            )))
        body.append(Verbatim('textconcat {} {} {}'.format(
            result.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))

        for each in args[2:]:
            rhs_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = rhs_slot,
                expr = each,
            )
            arg_t = sc.type_of(rhs_slot)
            if arg_t.to_string() != Type.string().to_string():
                is_pointer = (type(arg_t) is viuact.typesystem.t.Pointer)
                dereference_freely = (not rhs_slot.inhibit_dereference())
                deref = (is_pointer and dereference_freely)
                body.append(Verbatim('text {} {}'.format(
                    rhs_slot.to_string(),
                    rhs_slot.as_pointer(deref).to_string(),
                )))
            body.append(Verbatim('textconcat {} {} {}'.format(
                result.to_string(),
                result.to_string(),
                rhs_slot.to_string(),
            )))

        st.type_of(result, Type.string())

    return result

def emit_arithmetic_operator(mod, body, st, result, expr):
    if len(expr.arguments()) < 2:
        raise viuact.errors.Invalid_arity(
            pos = expr.operator().tok().at(),
            s = str(expr.operator()),
            kind = viuact.errors.Invalid_arity.OPERATOR,
        ).note('expected at least 2 arguments, got {}'.format(
            len(expr.arguments()),
        ))

    operator_ops = {
        '+': 'add',
        '-': 'sub',
        '*': 'mul',
        '/': 'div',
    }
    op = operator_ops[str(expr.operator().tok())]

    with st.scoped() as sc:
        lhs_slot = sc.get_slot(None)
        rhs_slot = sc.get_slot(None)

        args = expr.arguments()

        lhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = lhs_slot,
            expr = args[0],
        )
        rhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = rhs_slot,
            expr = args[1],
        )
        body.append(Verbatim('{} {} {} {}'.format(
            op,
            result.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))

        ret_t = sc.type_of(lhs_slot)
        if not Type.Int.is_integer_type(ret_t):
            raise viuact.errors.Type_mismatch(
                pos = args[0].first_token().at(),
                a = '<any integer type>',
                b = ret_t.to_string(),
            ).note('arithmetic operator {} requires integer operands'.format(
                str(expr.operator().tok()),
            ))

        sc.unify_types(ret_t, sc.type_of(rhs_slot))

        for each in args[2:]:
            rhs_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = rhs_slot,
                expr = each,
            )
            sc.unify_types(ret_t, sc.type_of(rhs_slot))
            body.append(Verbatim('{} {} {} {}'.format(
                op,
                result.to_string(),
                result.to_string(),
                rhs_slot.to_string(),
            )))

        sc.deallocate_slot(lhs_slot)
        sc.deallocate_slot(rhs_slot)

        st.type_of(result, ret_t)

    return result

def emit_comparison_operator(mod, body, st, result, expr):
    if len(expr.arguments()) != 2:
        raise viuact.errors.Invalid_arity(
            pos = expr.operator().tok().at(),
            s = str(expr.operator()),
            kind = viuact.errors.Invalid_arity.OPERATOR,
        ).note('expected 2 arguments, got {}'.format(
            len(expr.arguments()),
        ))

    operator_ops = {
        '>':  'gt',
        '>=': 'gte',
        '<':  'lt',
        '<=': 'lte',
        '=':  'eq',
        '!=': 'eq',
    }
    op = operator_ops[str(expr.operator().tok())]

    with st.scoped() as sc:
        lhs_slot = sc.get_slot(None)
        rhs_slot = sc.get_slot(None)

        args = expr.arguments()

        lhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = lhs_slot,
            expr = args[0],
        )
        rhs_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = rhs_slot,
            expr = args[1],
        )
        body.append(Verbatim('{} {} {} {}'.format(
            op,
            result.to_string(),
            lhs_slot.to_string(),
            rhs_slot.to_string(),
        )))
        if str(expr.operator().tok()) == '!=':
            body.append(Verbatim('not {}'.format(result.to_string())))

        sc.deallocate_slot(lhs_slot)
        sc.deallocate_slot(rhs_slot)

        st.type_of(result, Type.bool())

    return result

def emit_operator_call(mod, body, st, result, expr):
    ARITHMETIC_OPERATORS = (
        viuact.lexemes.Operator_plus,
        viuact.lexemes.Operator_minus,
        viuact.lexemes.Operator_star,
        viuact.lexemes.Operator_solidus,
    )
    CMP_OPERATORS = (
        viuact.lexemes.Operator_lte,
        viuact.lexemes.Operator_lt,
        viuact.lexemes.Operator_gte,
        viuact.lexemes.Operator_gt,
        viuact.lexemes.Operator_neq,
        viuact.lexemes.Operator_eq,
    )
    if type(expr.operator()) is viuact.lexemes.Operator_concat:
        return emit_operator_concat(mod, body, st, result, expr)
    elif type(expr.operator()) in ARITHMETIC_OPERATORS:
        return emit_arithmetic_operator(mod, body, st, result, expr)
    elif type(expr.operator()) in CMP_OPERATORS:
        return emit_comparison_operator(mod, body, st, result, expr)
    raise None

def emit_enum_ctor_call(mod, body, st, result, form):
    from_module = form.to().module()
    enum_name = form.to().of_enum()
    enum_field = form.to().field()

    enum = (
        mod.module(from_module).enum(enum_name)
        if from_module else
        mod.enum(enum_name)
    )

    field = enum['fields'][str(enum_field)]

    # FIXME embed typing requirement into the list...
    ts = []
    for each in enum['template_parameters']:
        # FIXME ...instead of checking it here
        ts.append(Alt(
            I(viuact.typesystem.t.Base),
            T(viuact.typesystem.t.Template),
        ) | st.register_template_variable(each))

    body.append(Verbatim('struct {}'.format(result.to_string())))
    enum_t = st.type_of(result, viuact.typesystem.t.Value(
        name = str(enum_name),
        templates = tuple(ts),
    ))

    with st.scoped() as sc:
        key = sc.get_slot(name = None)
        body.append(Ctor(
            of_type = 'atom',
            slot = key,
            value = repr('key'),
        ))

        value = sc.get_slot(name = None)
        body.append(Ctor(
            of_type = 'integer',
            slot = value,
            value = field['index'],
        ))

        body.append(Verbatim('structinsert {} {} {}'.format(
            result.to_string(),
            key.to_string(),
            value.to_string(),
        )))

        if not field['field'].bare():
            body.append(Ctor(
                of_type = 'atom',
                slot = key,
                value = repr('value'),
            ))
            value_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = value,
                expr = form.value(),
            )
            body.append(Verbatim('structinsert {} {} {}'.format(
                result.to_string(),
                key.to_string(),
                value_slot.to_string(),
            )))

            value_t = sc.type_of(value_slot)
            field_t = viuact.typesystem.t.Value(
                name = str(enum_name),
                templates = (value_t,),
            )
            st.unify_types(enum_t, field_t)

        sc.deallocate_slot(key)
        sc.deallocate_slot(value)

    return result

def emit_primitive_literal(mod, body, st, result, expr):
    lit = expr.value()
    if type(lit) == viuact.lexemes.String:
        body.append(Ctor(
            of_type = 'text',
            slot = result,
            value = str(lit),
        ))
        st.type_of(result, Type.string())
        return result
    if type(lit) == viuact.lexemes.Integer:
        body.append(Ctor(
            of_type = 'integer',
            slot = result,
            value = str(lit),
        ))
        st.type_of(result, Type.i64())
        return result
    if type(lit) == viuact.lexemes.Bool_literal:
        body.append(Ctor(
            of_type = 'integer',
            slot = result,
            value = ('0' if str(lit) == 'true' else '1'),
        ))
        body.append(Verbatim('not {} {}'.format(
            result.to_string(),
            result.to_string(),
        )))
        st.type_of(result, Type.bool())
        return result
    viuact.util.log.fixme('failed to emit primitive literal: {}'.format(
        typeof(lit)))
    raise None

def emit_let_binding(mod, body, st, binding):
    name = binding.name()
    body.append(Verbatim('; let {} = ...'.format(str(name))))
    slot = st.get_slot(
        name = str(name),
        register_set = Register_set.LOCAL,
    )
    with st.scoped() as sc:
        slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            # Don't use an additional scope here as let-bindings should introduce
            # new variables into the current scope.
            result = slot,
            expr = binding.val(),
        )
    body.append(Verbatim(''))
    return slot

def emit_compound_expr(mod, body, st, result, expr):
    for i, each in enumerate(expr.body()):
        last = (i == (len(expr.body()) - 1))
        slot = None
        if type(each) is viuact.forms.Let_binding:
            slot = emit_let_binding(
                mod = mod,
                body = body,
                st = st,
                binding = each,
            )
        else:
            with st.scoped() as sc:
                slot = emit_expr(
                    mod = mod,
                    body = body,
                    st = sc,
                    result = (result if last else Slot.make_void()),
                    expr = each,
                )
        if last:
            result = slot
    return result

def emit_if(mod, body, st, result, expr):
    guard_slot = st.get_slot(name = None)
    with st.scoped() as sc:
        guard_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = guard_slot,
            expr = expr.guard(),
        )

    label_base = '{}+{}+{}'.format(
        mod.name(),
        st.fn(),
        st.special(),
    )
    label_core = hashlib.sha1(label_base.encode('utf-8')).hexdigest()
    label_true = 'if_true_' + label_core
    label_false = 'if_false_' + label_core
    label_end = 'if_end_' + label_core

    body.append(Verbatim('if {} {} {}'.format(
        guard_slot.to_string(),
        label_true,
        label_false,
    )))
    st.deallocate_slot_if_anonymous(guard_slot)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_true)))
    true_arm_t = None
    with st.scoped() as sc:
        slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = (sc.get_anonymous_slot() if result.is_void() else result),
            expr = expr.arm_true(),
        )
        body.append(Verbatim('jump {}'.format(label_end)))
        if not slot.is_void():
            true_arm_t = sc.type_of(slot)

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_false)))
    false_arm_t = None
    with st.scoped() as sc:
        slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = (sc.get_anonymous_slot() if result.is_void() else result),
            expr = expr.arm_false(),
        )
        if not slot.is_void():
            false_arm_t = sc.type_of(slot)

    if not Slot.is_void(result):
        st.unify_types(true_arm_t, false_arm_t)
    # sig = mod.signature(st.fn())
    # m, template_parameters = true_arm_t.match(false_arm_t, {})
    # if (not result.is_void()) and (true_arm_t != false_arm_t):
    #     # FIXME viuact.forms.If should record first token pointing to the if
    #     raise viuact.errors.If_arms_return_different_types(
    #         expr.first_token().at(),
    #         true_arm_t,
    #         false_arm_t,
    #     )

    body.append(Verbatim(''))
    body.append(Verbatim('.mark: {}'.format(label_end)))

    st.actual_pressure(Register_set.LOCAL)

    return result

def emit_match(mod, body, st, result, expr):
    if not expr.arms():
        raise viuact.errors.Match_with_no_arms(
            expr.first_token().at(),
        )

    guard_slot = st.get_slot(name = None)
    with st.scoped() as sc:
        guard_slot = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = guard_slot,
            expr = expr.guard(),
        )
    guard_t = st.type_of(guard_slot)

    enum_definition = mod.enum(guard_t.name())

    # The guard_key_slot holds the key of the enum produces by the guard
    # expression. It will be compared with keys of the with-clauses ("match
    # arms") to see which expression should be executed.
    guard_key_slot = st.get_slot(name = None)
    body.append(Ctor(
        of_type = 'atom',
        slot = guard_key_slot,
        value = repr('key'),
    ))
    body.append(Verbatim('structat {} {} {}'.format(
        guard_key_slot.to_string(),
        guard_slot.to_string(),
        guard_key_slot.to_string(),
    )))
    guard_key_slot = guard_key_slot.as_pointer()

    # The check_slot is used to hold the result of key comparison between the
    # guard expression and with-claus. It can be safely deallocated after the
    # comparisons are done.
    check_slot = st.get_slot(name = None)

    labelled_arms = []
    for arm in expr.arms():
        n = st.special()

        fmt_base = 'with_clause_{}'.format(n)
        arm_id = hashlib.sha1(fmt_base.encode('utf-8')).hexdigest()
        arm_expression_label = 'with_arm_expr_{}'.format(arm_id)
        arm_condition_label = 'with_arm_cond_{}'.format(arm_id)

        labelled_arms.append({
            'expr_label': arm_expression_label,
            'cond_label': arm_condition_label,
            'id': arm_id,
            'arm': arm,
        })
    done_fmt = 'match_done_{}'
    done_label = done_fmt.format(
        hashlib.sha1(done_fmt.format(st.special()).encode('utf-8')).hexdigest())

    # Emit code that compares enum value's tag to different fields of the enum,
    # and dispatches to appropriate with-clause or throws an error. This error
    # is more like assertion in that it should never be triggered (missing cases
    # should be handled at compile time), but let's leave it there just in case.
    #
    # The loop below emits the comparison code.
    catchall_encountered = False
    for i, arm in enumerate(labelled_arms):
        is_catchall = (str(arm['arm'].tag()) == '_')

        if is_catchall:
            catchall_encountered = True

            body.append(Comment(
                'jump to catch-all with-clause'
            ))
            body.append(Marker(label = arm['cond_label']))
            body.append(Jump(
                label = arm['expr_label'],
            ))
        else:
            body.append(Comment(
                'check for with-clause of {}'.format(arm['arm'].tag())
            ))
            body.append(Marker(label = arm['cond_label']))
            body.append(Ctor(
                of_type = 'integer',
                slot = check_slot,
                value = enum_definition['fields'][str(arm['arm'].tag())]['index'],
            ))
            body.append(Cmp(
                kind = Cmp.EQ,
                slot = check_slot,
                rhs = guard_key_slot,
                lhs = check_slot,
            ))
            body.append(If(
                cond = check_slot,
                if_true = arm['expr_label'],
                if_false = (
                    labelled_arms[i + 1]['cond_label']
                    if (i < (len(labelled_arms) - 1)) else
                    done_label
                ),
            ))

    # This is the error handling code handling that runs in case of unmatched
    # enum values. Should never be run, unless the compiler fucked up and did
    # not find a missing case.
    if True:
        body.append(Comment(
            'trigger an error in case nothing matched'
        ))
        body.append(Ctor(
            of_type = 'atom',
            slot = check_slot,
            value = repr('Match_failed'),
        ))
        body.append(Verbatim('exception {} {} void'.format(
            check_slot.to_string(),
            check_slot.to_string(),
        )))
        body.append(Verbatim('throw {}'.format(
            check_slot.to_string(),
        )))

    # Result slots of match-expressions are not disposable since they have a
    # very real effect - they consume their inputs, and this effect must be
    # enforced. Also, we can't have the result slot cancelled or all hell breaks
    # loose (the compiler crashes, for example).
    if result.is_disposable():
        result = result.as_disposable(False)

    # Emit the code that actually executes the with-clauses after the
    # "supporting" code has already been pushed to the body. Keep the type each
    # arm produces to compare them later - all arms must produce the same type
    # if we want to ensure consistency!
    arm_ts = []
    matched_tags = []
    for i, arm in enumerate(labelled_arms):
        # The markers are needed because the code detecting which arm (or:
        # with-clause) to execute uses them for jump targets.
        body.append(Verbatim(''))

        is_catchall = (str(arm['arm'].tag()) == '_')
        if is_catchall:
            body.append(Comment(
                'expression for catch-all with-clause'
            ))
        else:
            body.append(Comment(
                'expression for with-clause of {}'.format(arm['arm'].tag())
            ))
            matched_tags.append(arm['arm'].tag())
        body.append(Marker(label = arm['expr_label']))

        with st.scoped() as sc:
            # Remember to extract the "payload" of the enum value if the arm is
            # not bare, ie. if it provides a name to which the payload value
            # shall be bound.
            if not arm['arm'].bare():
                body.append(Ctor(
                    of_type = 'atom',
                    slot = check_slot,
                    value = Ctor.TAG_ENUM_VALUE_FIELD,
                ))
                value_slot = sc.get_slot(name = str(arm['arm'].name()))
                # Why use structuremove instead of structat instruction? Because
                # we consider the enum value to be "consumed" after the match
                # expression. If the programmer wants to avoid this they can
                # always copy the value before matching it.
                body.append(Verbatim('structremove {} {} {}'.format(
                    value_slot.to_string(),
                    guard_slot.to_string(),
                    check_slot.to_string(),
                )))

                temp_t = guard_t.templates()[0]
                sc.type_of(value_slot, temp_t)

            arm_slot = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = (sc.get_slot(None) if result.is_void() else result),
                expr = arm['arm'].expr(),
            )
            arm_ts.append(sc.type_of(arm_slot))

        # A jump after the last with-clause would be redundant and would cause
        # the assembler to complain about "useless jump" so let's not emit it.
        if i == (len(labelled_arms) - 1):
            continue
        body.append(Jump(label = done_label))
    body.append(Marker(label = done_label))
    body.append(Verbatim(''))

    if len(matched_tags) != len(enum_definition['fields']):
        matched_fields = list(map(lambda _: str(_), matched_tags))
        for field in enum_definition['fields'].values():
            field = field['field']
            if ((str(field.name()) not in matched_fields) and not
                    catchall_encountered):
                raise viuact.errors.Missing_with_clause(
                    expr.guard().first_token().at(),
                    str(field.name()),
                    str(guard_t.name()),
                )

        already_matched = []
        for field in matched_tags:
            if str(field) in already_matched:
                raise viuact.errors.Duplicated_with_clause(
                    field.tok().at(),
                    str(field),
                    str(guard_t.name()),
                )
            already_matched.append(str(field))

        if not catchall_encountered:
            raise viuact.errors.Mismatched_with_clauses(
                expr.guard().first_token().at(),
                str(guard_t.name()),
            )

    # Remember to compare types returned by each arm. They must all be the same!
    if not result.is_void():
        i = 1
        while i < len(arm_ts):
            a = arm_ts[i - 1]
            b = arm_ts[i]

            try:
                st.unify_types(a, b)
            except viuact.typesystem.state.Cannot_unify as e:
                a_t, b_t = e.args
                raise viuact.errors.Type_mismatch(
                    expr.arms()[i].tag().tok().at(),
                    a_t,
                    b_t,
                ).note('between tags {} and {}'.format(
                    str(expr.arms()[i - 1].tag()),
                    str(expr.arms()[i].tag()),
                )).note('all with-clauses must return the same type')

            i += 1

        st.type_of(result, arm_ts[0])

    st.deallocate_slot(check_slot)
    st.deallocate_slot(guard_key_slot)

    # The guard slot value is consumed. If it was a variable it is destroyed and
    # shall not be available after the match-expression that consumed it.
    #
    # FIXME It would be *INCREDIBLY* useful to record the place and reason of
    # deallocation of a slot (and its associated value) to provide better error
    # messages -- see what Rust's compiler is able to do (or look at newer GCC
    # and Clang).
    st.deallocate_slot(guard_slot)
    # st.deallocate_slot_if_anonymous(guard_slot)

    # raise None
    return result

def emit_fn_ref(mod, body, st, result, expr):
    fn_name = str(expr.name())
    candidates = list(filter(
        lambda x: x[1]['base_name'] == fn_name,
        mod.fns(),
    ))

    # We can assume that there is always at least one candidate because this
    # function's only caller is emit_name_ref() - which calls it when it detects
    # that the name to be emitted is a name of a function.
    the_one = None
    if len(candidates) == 1:
        the_one = candidates[0][1]
    else:
        raise None  # FIXME handle more than one candidate

    fn_full_name = '{}/{}'.format(fn_name, the_one['arity'])
    body.append(Verbatim('function {} {}'.format(
        result.to_string(),
        fn_full_name,
    )))
    fn_sig = mod.signature(fn_full_name)

    parameter_types = []
    tmp = {}
    for each in fn_sig['template_parameters']:
        tmp[viuact.typesystem.t.Template(each.name()[1:])] = st.register_template_variable(each)
    for each in fn_sig['parameters']:
        if type(each) is viuact.typesystem.t.Value:
            parameter_types.append(each.concretise(tmp))
        elif type(each) is viuact.typesystem.t.Fn:
            parameter_types.append(each.concretise(tmp))
        elif type(each) is viuact.typesystem.t.Template:
            parameter_types.append(each.concretise(tmp))
        else:
            raise None

    st.type_of(result, viuact.typesystem.t.Fn(
        rt = fn_sig['return'].concretise(tmp),
        pt = tuple(parameter_types),
        templates = tuple(tmp.values()),
    ))

    return result

def emit_name_ref(mod, body, st, result, expr):
    if any(map(lambda x: x[1]['base_name'] == str(expr.name()), mod.fns())):
        return emit_fn_ref(mod, body, st, result, expr)

    if result.is_void():
        viuact.util.log.raw('void slot for name-ref to {}'.format(
            str(expr.name()),
        ))
        raise None
    if result.is_disposable():
        # viuact.util.log.raw('cancelled disposable slot {} for name-ref to {}'.format(
        #     result.to_string(),
        #     str(expr.name()),
        # ))
        st.cancel_slot(result)
        return st.slot_of(str(expr.name())).inhibit_dereference(result.inhibit_dereference())
    else:
        slot = st.slot_of(str(expr.name()))
        # viuact.util.log.raw('move to {} from {} for name-ref to {}'.format(
        #     result.to_string(),
        #     slot.to_string(),
        #     str(expr.name()),
        # ))
        t = st.type_of(slot)
        st.name_slot(result, str(expr.name()))
        if result.inhibit_dereference():
            # viuact.util.log.raw('name-ref creates a pointer: {} <- {}'.format(
            #     result.to_string(),
            #     slot.to_string(),
            # ))
            st.type_of(result, viuact.typesystem.t.Pointer(t))
            body.append(Move.make_pointer(
                source = slot,
                dest = result,
            ))
        else:
            st.type_of(result, t)
            st.deallocate_slot(slot)
            body.append(Move.make_move(
                source = slot,
                dest = result,
            ))
        return result

def emit_throw(mod, body, st, result, expr):
    with st.scoped() as sc:
        ex = mod.exception(expr.tag())

        if ex and expr.bare():
            raise viuact.errors.Invalid_arity(
                pos = expr.tag().tok().at(),
                s = str(expr.tag()),
                kind = viuact.errors.Invalid_arity.EX_CTOR,
            ).note(
                'value is expected'
            ).note(
                '(throw {ex} <value>) instead of (throw {ex})'.format(
                    ex = str(expr.tag()),
                ),
            )

        if not ex and not expr.bare():
            raise viuact.errors.Invalid_arity(
                pos = expr.tag().tok().at(),
                s = str(expr.tag()),
                kind = viuact.errors.Invalid_arity.EX_CTOR,
            ).note(
                '{} is a bare exception'.format(str(expr.tag()))
            )

        value = Slot.make_void()
        if not expr.bare():
            value = sc.get_slot(None)
            value = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = value,
                expr = expr.value(),
            )

        tag = sc.get_slot(None)
        body.append(Ctor(
            of_type = 'atom',
            slot = tag,
            value = repr(str(expr.tag())),
        ))

        if result.is_void():
            result = sc.get_slot(None)

        body.append(Verbatim('exception {} {} {}'.format(
            result.to_string(),
            tag.to_string(),
            value.to_string(),
        )))
        body.append(Verbatim('throw {}'.format(
            result.to_string(),
        )))
        body.append(Verbatim(''))
    return result

def emit_catch_arm(mod, body, st, result, expr):
    exception_slot = (
        st.get_slot(None)
        if expr.bare() else
        st.get_slot(name = str(expr.name()))
    )

    ex_t = mod.exception(str(expr.tag()))
    if (not expr.bare()) and ex_t is None:
        raise viuact.errors.Bind_of_exception_with_no_value(
            expr.first_token().at(),
            expr.tag(),
            expr.name(),
        )

    body.append(Verbatim('draw {}'.format(exception_slot.to_string())))

    if expr.bare():
        body.append(Verbatim('delete {}'.format(exception_slot.to_string())))
        st.deallocate_slot(exception_slot)
        exception_slot = Slot.make_void()
    else:
        body.append(Verbatim('exception_value {ex} {ex}'.format(
            ex = exception_slot.to_string(),
        )))
        st.type_of(exception_slot, viuact.typesystem.t.Value(
            name = str(ex_t.name()),
        ))

    result_slot = emit_expr(
        mod = mod,
        body = body,
        st = st,
        result = result,
        expr = expr.expr(),
    )
    body.append(Verbatim('leave'))

    return result_slot

def emit_try(mod, body, st, result, expr):
    if not expr.arms():
        raise viuact.errors.Try_with_no_arms(
            expr.first_token().at(),
        )

    try_arm_id = hashlib.sha1(
        'try_arm_{}'.format(st.special()).encode('utf-8')).hexdigest()
    try_arm_name = 'try_arm_{}'.format(try_arm_id)

    arms = []
    for arm in expr.arms():
        fmt_base = 'catch_arm_{}'.format(st.special())
        arm_id = hashlib.sha1(fmt_base.encode('utf-8')).hexdigest()
        arm_name = 'catch_arm_{}'.format(arm_id)
        arms.append({
            'exception': arm.tag(),
            'block_id': arm_name,
            'expression': arm,
        })

    body.append(Verbatim('try'))

    for arm in arms:
        body.append(Verbatim('catch {} .block: {}'.format(
            repr(str(arm['exception'])),
            arm['block_id'],
        )))
        with st.scoped() as sc:
            emit_catch_arm(
                mod = mod,
                body = body,
                st = sc,
                result = result,
                expr = arm['expression'],
            )
        body.append(Verbatim('.end'))

    body.append(Verbatim('enter .block: {}'.format(try_arm_name)))
    result = emit_expr(
        mod = mod,
        body = body,
        st = st,
        result = result,
        expr = expr.guard(),
    )
    body.append(Verbatim('leave'))
    body.append(Verbatim('.end'))

    return result

def emit_record_ctor(mod, body, st, result, expr):
    record_type = expr.name()

    body.append(Ctor(
        of_type = 'struct',
        slot = result,
        value = '',
    ))
    st.type_of(result, viuact.typesystem.t.Value(
        name = str(record_type.name()),
    ))

    record_definition = mod.record(record_type.name())

    with st.scoped() as sc:
        field_name = sc.get_slot(None)
        field_value = sc.get_slot(None)

        for each in expr.fields():
            r = emit_expr(
                mod = mod,
                body = body,
                st = sc,
                result = field_value,
                expr = each.value(),
            )

            r_t = sc.type_of(r)
            # FIXME fix this ugliness and store field types properly, as types,
            # and not as strings
            field_t = str(record_definition['fields'][str(each.name())])
            if field_t == 'i8':
                field_t = Type.i8()
            elif field_t == 'i16':
                field_t = Type.i16()
            else:
                field_t = viuact.typesystem.t.Value(
                    name = field_t,
                )
            try:
                st.unify_types(field_t, r_t)
            except viuact.typesystem.state.Cannot_unify:
                raise viuact.errors.Bad_type_of_record_field(
                    pos = each.value().first_token().at(),
                    record = str(record_type.name()),
                    field = str(each.name()),
                    declared = field_t.to_string(),
                    actual = r_t.to_string(),
                )


            body.append(Ctor(
                of_type = 'atom',
                slot = field_name,
                value = repr(str(each.name())),
            ))
            body.append(Verbatim('structinsert {} {} {}'.format(
                result.to_string(),
                field_name.to_string(),
                field_value.to_string(),
            )))

    return result

def emit_record_field_access(mod, body, st, result, expr):
    with st.scoped() as sc:
        base = sc.get_disposable_slot()
        base = emit_expr(
            mod = mod,
            body = body,
            st = sc,
            result = base,
            expr = expr.base(),
        )

        record_t = sc.type_of(base)
        pointered_base = (type(record_t) is viuact.typesystem.t.Pointer)
        record_definition = (
            mod.record(record_t.to().name())
            if pointered_base
            else mod.record(record_t.name())
        )

        field = sc.get_slot(None)
        body.append(Ctor(
            of_type = 'atom',
            slot = field,
            value = repr(str(expr.field())),
        ))
        # FIXME use structremove and consume fields if possible (try to detect
        # such opportunities); copying is expensive
        body.append(Verbatim('structat {} {} {}'.format(
            result.to_string(),
            (base.as_pointer() if pointered_base else base).to_string(),
            field.to_string(),
        )))

        field_t = viuact.typesystem.t.Value(
            name = str(record_definition['fields'][str(expr.field())]),
        )
        if result.inhibit_dereference():
            field_t = viuact.typesystem.t.Pointer(field_t)

        # FIXME register the type in case of templates
        st.type_of(result, field_t)
    return result

def emit_expr(mod, body, st, result, expr):
    if type(expr) is viuact.forms.Fn_call:
        return emit_fn_call(
            mod = mod,
            body = body,
            st = st,
            result = result,
            form = expr,
        )
    if type(expr) is viuact.forms.Operator_call:
        return emit_operator_call(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Compound_expr:
        return emit_compound_expr(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Primitive_literal:
        return emit_primitive_literal(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Name_ref:
        try:
            return emit_name_ref(mod, body, st, result, expr)
        except KeyError:
            raise viuact.errors.Read_of_unbound_variable(
                expr.name().tok().at(),
                str(expr.name()),
            )
    if type(expr) is viuact.forms.Let_binding:
        if not result.is_void():
            st.cancel_slot(result)
        return emit_let_binding(
            mod = mod,
            body = body,
            st = st,
            binding = expr,
        )
    if type(expr) is viuact.forms.If:
        return emit_if(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Enum_ctor_call:
        return emit_enum_ctor_call(
            mod = mod,
            body = body,
            st = st,
            result = result,
            form = expr,
        )
    if type(expr) is viuact.forms.Match:
        return emit_match(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Throw:
        return emit_throw(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Try:
        return emit_try(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Record_ctor:
        return emit_record_ctor(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Record_field_access:
        return emit_record_field_access(
            mod = mod,
            body = body,
            st = st,
            result = result,
            expr = expr,
        )
    if type(expr) is viuact.forms.Inhibit_dereference:
        return emit_expr(
            mod = mod,
            body = body,
            st = st,
            result = result.inhibit_dereference(True),
            expr = expr.expr(),
        )
    viuact.util.log.fixme('failed to emit expression: {}'.format(
        typeof(expr)))
    raise None
