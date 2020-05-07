from viuact import exceptions, token_types, group_types


def group_impl(tokens, break_on = token_types.Right_paren):
    grouped = [tokens[0]]

    i = 1
    while i < len(tokens):
        each = tokens[i]

        if isinstance(each, token_types.Left_curly) and isinstance(grouped[-1], token_types.Left_paren):
            raise exceptions.Unexpected_token(
                'opening curly brace cannot follow opening parenthesis',
                each,
            )

        if isinstance(each, token_types.Left_paren):
            g, n = group_impl(tokens[i:])
            grouped.append(g[1:-1])
            i += n
            continue

        if isinstance(each, token_types.Dot):
            name_types = (token_types.Module_name, token_types.Name,)
            if type(tokens[i+1]) not in name_types:
                raise Exception('expected module name or name to follow operator dot, got', tokens[i+1])

            if type(grouped[-1]) in name_types and type(tokens[i+1]) in name_types:
                grouped[-1] = [each, grouped[-1], tokens[i+1]]
                i += 2
                continue

            if type(grouped[-1]) is list:
                grouped[-1] = [each, grouped[-1], tokens[i+1],]
                i += 2
                continue

            raise Exception('operator dot should not appear here')

        if isinstance(each, token_types.Catch):
            name_types = (token_types.Module_name, token_types.Name,)
            if type(tokens[i+1]) not in (token_types.Module_name, token_types.Name):
                raise Exception('expected exception tag to follow catch, got', tokens[i+1])
            grouped.append([
                token_types.Exception_tag_name(tokens[i+1].token),
            ])
            i += 1
            continue

        if isinstance(each, token_types.Left_curly):
            g, n = group_impl(
                tokens[i:],
                break_on = token_types.Right_curly,
            )
            grouped.append([ token_types.Compound_expression_marker(tokens[i]) ] + [ g[1:-1] ])
            i += n
            continue

        grouped.append(each)
        i += 1

        if isinstance(each, break_on):
            break

    return grouped, i

def group(tokens):
    """Grouping turns a stream of tokens into a stream of groups representing
    nested expressions surrounded by ().
    """
    groups = []

    i = 0
    while i < len(tokens):
        each = tokens[i]
        g, n = group_impl(tokens[i:])
        groups.append(g[1:-1])
        i += n

    return groups


def parse_expression_impl(expr):
    """Parsing turns "anonymous" groups of tokens into syntactic entities.
    Let bindings, name references, function calls, etc.
    """
    leader = (expr[0] if type(expr) is list else expr)
    leader_type = type(leader)

    name_types = (token_types.Module_name, token_types.Name,)
    literal_types = (
        token_types.Integer,
        token_types.Float,
        token_types.String,
        token_types.Timeout,
        token_types.Boolean,
    )

    def can_be_considered_name(some_expr):
        if type(some_expr) is token_types.Name:
            return True
        if type(some_expr) is list and some_expr and type(some_expr[0]) in name_types:
            return True
        return False

    if leader_type is token_types.Let and len(expr) == 3:
        return group_types.Let_binding(
            name = expr[1],
            value = parse_expression(expr[2]),
        )
    elif leader_type is token_types.Let and len(expr) == 4:
        return parse_function(expr)
    elif leader_type is token_types.Dot:
        return group_types.Id(
            # FIXME Maybe also parse the third element of the expression, that
            # is - the field name?
            name = [expr[0], parse_expression(expr[1]), expr[2],],
        )
    elif leader_type is token_types.Name and type(expr) is list:
        return group_types.Function_call(
            name = expr[0],
            args = [parse_expression(each) for each in expr[1:]],
        )
    elif leader_type is list and (type(leader[0]) in name_types or type(leader[0]) is token_types.Dot):
        return group_types.Function_call(
            name = parse_expression(expr[0]),
            args = [parse_expression(each) for each in expr[1:]],
        )
    elif leader_type is token_types.Name:
        return group_types.Name_ref(
            name = expr,
        )
    elif leader_type is token_types.Labeled_parameter_name:
        if type(expr) is list:
            return group_types.Argument_bind(
                name = leader,
                expr = parse_expression(expr[1]),
            )
        else:
            # This is for label punning, so we can write code like this:
            #
            #   (let fn (~a ~b) ...)
            #
            #   (let a 1)
            #   (let b 2)
            #   (fn ~b ~a)
            #
            # instead of:
            #
            #   (let (~b b) (~a a))
            #
            # which would be silly. Instead, we let the compiler automatically
            # infer the label to which the argument should be bound. Make the
            # machine work for us.
            return group_types.Argument_bind(
                name = leader,
                expr = parse_expression(token_types.Name(str(leader.token)[1:])),
            )
    elif leader_type in token_types.OPERATOR_TYPES and type(expr) is list:
        return group_types.Operator_call(
            operator = expr[0],
            args = [parse_expression(each) for each in expr[1:]],
        )
    elif leader_type is token_types.Pointer_dereference and type(expr) is list:
        return group_types.Pointer_dereference(
            value = parse_expression(expr[1]),
        )
    elif leader_type is token_types.Field_assignment and type(expr) is list:
        return group_types.Field_assignment(
            operator = expr[0],
            field = expr[1],
            value = parse_expression(expr[2]),
        )
    elif leader_type is token_types.If:
        return group_types.If(
            condition = parse_expression(expr[1]),
            arms = [parse_expression(each) for each in expr[2:]],
        )
    elif leader_type in literal_types:
        return expr
    elif leader_type is token_types.Actor and can_be_considered_name(expr[1]):
        return group_types.Actor_call(
            name = parse_expression(expr[1]),
            args = [parse_expression(each) for each in expr[2:]],
        )
    elif leader_type is token_types.Tailcall and can_be_considered_name(expr[1]):
        return group_types.Tail_call(
            name = parse_expression(expr[1]),
            args = [parse_expression(each) for each in expr[2:]],
        )
    elif leader_type is token_types.Defer and can_be_considered_name(expr[1]):
        return group_types.Deferred_call(
            name = parse_expression(expr[1]),
            args = [parse_expression(each) for each in expr[2:]],
        )
    elif leader_type is token_types.Watchdog and can_be_considered_name(expr[1]):
        return group_types.Watchdog_call(
            name = parse_expression(expr[1]),
            args = [parse_expression(each) for each in expr[2:]],
        )
    elif leader_type is token_types.Compound_expression_marker:
        return group_types.Compound_expression(
            expressions = [ parse_expression(each) for each in expr[1] ],
        )
    elif leader_type is token_types.Struct:
        return group_types.Struct()
    elif leader_type is token_types.Vector:
        init = []
        if len(expr) > 1:
            init = [parse_expression(each) for each in expr[1]]
        return group_types.Vector(init)
    elif leader_type is token_types.Try:
        return group_types.Try_expression(
            expr = parse_expression(expr[1]),
            handling_blocks = [
                group_types.Catch_expression(
                    tag = parse_expression(each[0]),
                    name = each[2],
                    expr = parse_expression(each[3]),
                )
                for each
                in expr[2]
            ],
        )
    elif leader_type is token_types.Match:
        return group_types.Match_expression(
            expr = parse_expression(expr[1]),
            handling_blocks = [
                (
                    group_types.With_expression(
                        pattern = parse_expression(each[1]),
                        name = None,
                        expr = parse_expression(each[2]),
                    )
                    if len(each) == 3
                    else
                    group_types.With_expression(
                        pattern = parse_expression(each[1]),
                        name = each[2],
                        expr = parse_expression(each[3]),
                    )
                )
                for each
                in expr[2]
            ],
        )
    elif leader_type is token_types.Exception_tag_name:
        return group_types.Exception_tag(tag = expr[0])
    elif leader_type is token_types.Module_name:
        return expr
    else:
        if leader_type is list:
            raise exceptions.Unexpected_group(
                'expected a single expression, got a list',
                exceptions.first_usable_token(expr),
            )
        raise Exception('invalid expression', leader_type, expr)

def parse_expression(expr):
    if type(expr) is list and not len(expr):
        raise exceptions.Unexpected_group(
            'a group cannot be empty',
            None
        )
    try:
        return parse_expression_impl(expr)
    except exceptions.Viuact_exception as e:
        raise exceptions.Fallout(
            token = exceptions.first_usable_token(expr),
            message = 'during parsing expression',
            cause = e,
        )

def parse_function(source):
    if not isinstance(source[1], token_types.Name):
        raise exceptions.make_fallout(source[1], 'expected name',
                exceptions.Unexpected_token('name', source[1]))
    if len(source) != 4:
        raise exceptions.make_fallout(source[1], 'invalid function definition',
                exceptions.Unexpected_token(source[1], source[1]))

    fn = group_types.Function(name = source[1])

    try:
        formal_parameters = source[2]
        if not isinstance(formal_parameters, list):
            raise exceptions.Unexpected_token('formal parameters list', formal_parameters)
        for each in formal_parameters:
            if not isinstance(each, token_types.Token_type):
                raise exceptions.Unexpected_token('a name', source[1])
            if type(each) not in (token_types.Labeled_parameter_name, token_types.Name,):
                raise exceptions.Unexpected_token('a name', each)
        fn.arguments = formal_parameters
    except exceptions.Viuact_exception as e:
        raise exceptions.Fallout(
            token = e.main_token,
            message = 'failed to parse formal parameters list',
            cause = e,
        )

    try:
        fn.body = parse_expression(source[3])
    except exceptions.Viuact_exception as e:
        raise exceptions.Fallout(
            token = source[1],
            message = 'failed to parse function body',
            cause = e,
        )

    return fn

def parse_module(source):
    if not isinstance(source[1], token_types.Module_name):
        raise Exception('expected module name, got', source[1])

    if len(source) == 2:
        return group_types.Module(name = source[1])

    mod = group_types.Inline_module(name = source[1])

    module_contents = source[2]
    for each in module_contents:
        if type(each[0]) is token_types.Let:
            fn = parse_function(each)
            mod.function_names.append(str(fn.name.token))
            mod.functions[mod.function_names[-1]] = fn
        elif type(each[0]) is token_types.Module:
            md = parse_module(each)
            mod.module_names.append(str(md.name.token))
            mod.modules[mod.module_names[-1]] = md
        elif type(each[0]) is token_types.Enum:
            mod.enums.append(parse_enum(each))
        elif type(each[0]) is token_types.Import:
            mod.imports.append(group_types.Import(name = group_types.Id(
                (each[1] if type(each[1]) is list else [each[1]]),
            )))
        else:
            raise Exception('expected `module`, `import`, or `let` keyword, got', each[0])

    return mod

def parse_enum_elements(source):
    elements = []
    for each in source:
        if type(each) is token_types.Module_name:
            elements.append(group_types.Enum_element(
                name = each,
                value = None,
            ))
        elif type(each) is list:
            elements.append(group_types.Enum_element(
                name = each[0],
                value = each[1],
            ))
    return elements

def parse_enum(source):
    if not isinstance(source[1], token_types.Module_name):
        raise Exception('expected enum name, got', source[1])

    return group_types.Enum_definition(
        name = source[1],
        values = parse_enum_elements(source[2]),
    )


def parse(groups):
    parsed = []

    for each in groups:
        leader = each[0]
        if isinstance(leader, token_types.Module):
            parsed.append(parse_module(each))
        elif isinstance(leader, token_types.Let):
            parsed.append(parse_function(each))
        elif type(each[0]) is token_types.Enum:
            parsed.append(parse_enum(each))
        elif isinstance(leader, token_types.Import):
            parsed.append(group_types.Import(name = group_types.Id(
                (each[1] if type(each[1]) is list else [each[1]]),
            )))
        else:
            raise Exception('invalid leader', leader)

    return parsed
