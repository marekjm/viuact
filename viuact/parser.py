import viuact.errors
import viuact.lexemes
import viuact.forms


def strip_comments(tokens):
    return list(filter(
        lambda each: each.t() is not viuact.lexemes.Comment, tokens))

def typeof(value):
    return str(type(value))[8:-2]


class G:
    @staticmethod
    def resolve_token(g):
        if type(g) is Group:
            return G.resolve_token(g.lead())
        elif type(g) is Element:
            return g.val().tok()

    @staticmethod
    def resolve_position(g):
        return G.resolve_token(g).at()

class Group(G):
    def __init__(self, value, tag):
        self._value = value
        self._tag = tag

    def __len__(self):
        return len(self.val())

    def __iter__(self):
        return iter(self.val())

    def __getitem__(self, n):
        return self.val()[n]

    def val(self):
        return self._value

    def lead(self):
        return self.val()[0]

    def tag(self):
        return self._tag

class Element(G):
    def __init__(self, value):
        self._value = value

    def __len__(self):
        return 1

    def __iter__(self):
        return iter([self.val()])

    def val(self):
        return self._value

    def lead(self):
        return self.val()

    def t(self):
        return self.val().t()


def group_one(tokens, i, g):
    sentinel = g[0]
    tag = None
    if sentinel.t() is viuact.lexemes.Left_paren:
        sentinel = viuact.lexemes.Right_paren
        tag = viuact.lexemes.Paren_tag(token = tokens[i - 1].tok())
        # g = [Element(tag)]
        g = []
    elif sentinel.t() is viuact.lexemes.Left_curly:
        sentinel = viuact.lexemes.Right_curly
        tag = viuact.lexemes.Curly_tag(token = tokens[i - 1].tok())
        g = [Element(tag)]
    else:
        raise viuact.errors.Invalid_sentinel(tokens[i - 1].at(), str(sentinel))

    while i < len(tokens):
        each = tokens[i]
        if each.t() in (viuact.lexemes.Left_paren, viuact.lexemes.Left_curly,):
            i, gp = group_one(tokens, i + 1, [each])
            g.append(gp)
            continue

        if each.t() in (
            viuact.lexemes.Right_paren, viuact.lexemes.Right_curly,) and each.t() is not sentinel:
            raise viuact.errors.Unbalanced_braces(pos = each.tok().at())

        i += 1
        if each.t() is sentinel:
            break

        g.append(Element(each))

    return i, Group(g, tag)

def group(tokens):
    groups = []

    i = 0
    while i < len(tokens):
        i, g = group_one(tokens, i + 1, [ tokens[i], ])
        groups.append(g)

    return groups


def parse_compound_expr(group):
    expressions = []

    for each in group[1:]:
        expressions.append(parse_expr(each))

    return viuact.forms.Compound_expr(expressions)

def parse_fn_call(group):
    kind = viuact.forms.Fn_call.Kind.Call
    offset = 0
    call_kind_toks = (
        viuact.lexemes.Tail,
    )
    if type(group[0]) is Element and group.lead().t() in call_kind_toks:
        offset = 1
        raise viuact.errors.Unexpected_token(G.resolve_position(group[0]),
            'call kinds are not implemented yet')

    name = group[0 + offset]
    if type(name) is Group:
        raise viuact.errors.Fail(G.resolve_position(name),
            'module paths are not implemented')
    elif type(name) is Element:
        name = parse_expr(name)
    else:
        raise viuact.errors.Unexpected_token(G.resolve_position(name),
            'expected function name, or a call-kind marker')

    args = []
    for each in group[1 + offset:]:
        args.append(parse_expr(each))

    return viuact.forms.Fn_call(
        to = name,
        arguments = args,
        kind = viuact.forms.Fn_call.Kind.Call,
    )

def parse_simple_expr(elem):
    if elem.t() is viuact.lexemes.Integer:
        return viuact.forms.Primitive_literal(value = elem.val())
    if elem.t() is viuact.lexemes.String:
        return viuact.forms.Primitive_literal(value = elem.val())
    if elem.t() is viuact.lexemes.Name:
        return viuact.forms.Name_ref(name = elem.val())
    viuact.util.log.fixme('failed to parse simple expression: {} {}'.format(
        typeof(elem.lead()), elem.lead()))
    raise None  # parse simple expressions

def parse_let_binding(group):
    name = group[1].val()
    if type(name) is not viuact.lexemes.Name:
        raise viuact.errors.Unexpected_token(
            name.tok().at(),
            str(name),
        ).note('expected name')
    return viuact.forms.Let_binding(
        name = name,
        value = parse_expr(group[2]),
    )

def parse_expr(group):
    if type(group) is Group:
        if type(group.tag()) is viuact.lexemes.Curly_tag:
            return parse_compound_expr(group)
        if not (type(group.tag()) is viuact.lexemes.Paren_tag):
            raise None
        if group.lead().t() is viuact.lexemes.Let and len(group.val()) == 3:
            return parse_let_binding(group)
        if group.lead().t() is viuact.lexemes.Let and len(group.val()) == 4:
            return parse_fn(group)
        return parse_fn_call(group)
    else:
        return parse_simple_expr(group)

def parse_fn_parameter(group):
    if type(group) is Element:
        name = group.val()
        if name.t() not in (viuact.lexemes.Name, viuact.lexemes.Labelled_name,):
            raise viuact.errors.Unexpected_token(
                pos = name.tok().at(),
                s = str(name),
            ).note('expected a name or a labelled name')

        return viuact.forms.Named_parameter(name)

    viuact.util.log.fixme(
        'defaulted parameters are not implemented', '<viuact>')
    raise viuact.errors.Unexpected_token(
        pos = group.tag().tok().at(),
        s = str(group.tag()),
    ).note('expected a defaulted parameter')

def parse_fn(group):
    name = group[1]
    if name.t() is not viuact.lexemes.Name:
        raise viuact.errors.Unexpected_token(
            pos = name.val().tok().at(),
            s = str(name.val()),
        ).note('expected a name')

    parameters = []
    for i, p in enumerate(group[2]):
        try:
            parameters.append(parse_fn_parameter(p))
        except viuact.errors.Error as e:
            raise e.then(viuact.errors.Info(
                pos = G.resolve_position(p),
                m = 'when parsing parameter {} of function {}'.format(
                    i, str(name.val()))))

    expression = parse_expr(group[3])

    return viuact.forms.Fn(
        name = name.val(),
        parameters = parameters,
        expression = expression,
    )

def parse_impl(groups):
    forms = []

    for g in groups:
        if g.lead().t() is viuact.lexemes.Let and len(g) == 3:
            print('a let binding')
        elif g.lead().t() is viuact.lexemes.Let and len(g) == 4:
            forms.append(parse_fn(g))

    return forms

def parse(tokens):
    no_comments = strip_comments(tokens)
    groups = group(no_comments)
    return parse_impl(groups)


def to_data(forms):
    data = []

    for each in forms:
        data.append(viuact.sl.data_of_form(each, None))

    return { 'forms': data, }
