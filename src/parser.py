import token_types
import group_types


def group_impl(tokens, break_on = token_types.Right_paren):
    grouped = [tokens[0]]

    i = 1
    while i < len(tokens):
        each = tokens[i]

        if isinstance(each, token_types.Left_paren):
            g, n = group_impl(tokens[i:])
            grouped.append(g[1:-1])
            i += n
            continue

        if isinstance(each, token_types.Dot):
            name_types = (token_types.Module_name, token_types.Name,)
            if not ((type(grouped[-1]) in name_types) or
                (type(grouped[-1]) is list and type(grouped[-1][-1]) in name_types)):
                raise Exception(
                    'operator dot must follow module name or name, got',
                    grouped[-1],
                    grouped[-1][-1],
                )
            if type(tokens[i+1]) not in (token_types.Module_name, token_types.Name):
                raise Exception('expected module name or name to follow operator dot, got', tokens[i+1])

            if type(grouped[-1]) is list:
                grouped[-1].extend([each, tokens[i+1],])
            else:
                grouped[-1] = [grouped[-1], each, tokens[i+1],]
            i += 2
            continue

        if isinstance(each, token_types.Left_curly):
            g, n = group_impl(tokens[i:], break_on = token_types.Right_curly)
            grouped.append([ token_types.Compound_expression_marker(tokens[i]) ] + [ g[1:-1] ])
            i += n
            continue

        grouped.append(each)
        i += 1

        if isinstance(each, break_on):
            return grouped, i

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


def parse_expression(expr):
    """Parsing turns "anonymous" groups of tokens into syntactic entities.
    Let bindings, name references, function calls, etc.
    """
    leader = (expr[0] if type(expr) is list else expr)
    leader_type = type(leader)

    name_types = (token_types.Module_name, token_types.Name,)
    literal_types = (token_types.Integer, token_types.String, token_types.Timeout)

    if leader_type is token_types.Let and len(expr) == 3:
        return group_types.Let_binding(
            name = expr[1],
            value = parse_expression(expr[2]),
        )
    elif leader_type is token_types.Let and len(expr) == 4:
        return parse_function(expr)
    elif leader_type is token_types.Name and type(expr) is list:
        return group_types.Function_call(
            name = expr[0],
            args = [parse_expression(each) for each in expr[1]],
        )
    elif leader_type is list and type(leader[0]) in name_types:
        return group_types.Function_call(
            name = parse_expression(expr[0]),
            args = [parse_expression(each) for each in expr[1]],
        )
    elif leader_type in name_types and type(expr) is list and type(expr[1]) is token_types.Dot:
        return group_types.Id(
            name = expr,
        )
    elif leader_type is token_types.Name:
        return group_types.Name_ref(
            name = expr,
        )
    elif isinstance(leader, (token_types.Logic_operator, token_types.Arithmetic_operator)) and type(expr) is list:
        return group_types.Operator_call(
            operator = expr[0],
            args = [parse_expression(each) for each in expr[1]],
        )
    elif leader_type is token_types.If:
        return group_types.If(
            condition = parse_expression(expr[1]),
            arms = [parse_expression(each) for each in expr[2:]],
        )
    elif leader_type in literal_types:
        return expr
    elif leader_type is token_types.Actor and type(expr[1]) is token_types.Name and type(expr[2]) is list:
        return group_types.Actor_call(
            name = parse_expression(expr[1]),
            args = [parse_expression(each) for each in expr[2]],
        )
    elif leader_type is token_types.Compound_expression_marker:
        return group_types.Compound_expression(
            expressions = [ parse_expression(each) for each in expr[1] ],
        )
    else:
        raise Exception('invalid expression in function body', expr)

def parse_function_body(source):
    body = []

    for each in source:
        body.append(parse_expression(each))

    return body

def parse_function(source):
    if not isinstance(source[1], token_types.Name):
        raise Exception('expected name, got', source[1])
    if len(source) != 4:
        raise Exception('invalid function definition')

    fn = group_types.Function(name = source[1])

    if not isinstance(source[2], list):
        raise Exception('expected arguments list, got', source[2])
    fn.arguments = source[2]

    if not isinstance(source[3], list):
        raise Exception('expected expression, got', source[3])
    fn.body = parse_function_body(source[3])

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
        elif type(each[0]) is token_types.Import:
            mod.imports.append(group_types.Import(name = group_types.Id(
                (each[1] if type(each[1]) is list else [each[1]]),
            )))
        else:
            raise Exception('expected `module`, `import`, or `let` keyword, got', each[0])

    return mod


def parse(groups):
    parsed = []

    for each in groups:
        leader = each[0]
        if isinstance(leader, token_types.Module):
            parsed.append(parse_module(each))
        elif isinstance(leader, token_types.Let):
            parsed.append(parse_function(each))
        elif isinstance(leader, token_types.Import):
            parsed.append(group_types.Import(name = group_types.Id(
                (each[1] if type(each[1]) is list else [each[1]]),
            )))
        else:
            raise Exception('invalid leader', leader)

    return parsed
