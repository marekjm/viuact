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


class Sentinels:
    def __init__(self):
        self._sentinels = []
        self._counter = 0
        self._popped = None

    def __iter__(self):
        return iter(self._sentinels)

    def push(self, sent):
        self._sentinels.append(sent)
        self._counter += 1
        return self

    def pop(self, at):
        print = lambda *args: sys.stderr.write('{}\n'.format(' '.join(
            map(str, args))))

        self._sentinels.pop()
        self._popped = at
        self._counter -= 1
        if len(self._sentinels) != self._counter:
            raise None
        return self

    def empty(self):
        return (len(self._sentinels) == 0)

    def popped(self):
        return self._popped

    def top(self):
        return self._sentinels[-1]

def group_one(tokens, i, delim, sentinels):
    sentinel = delim
    tag = None
    g = []
    if sentinel.t() is viuact.lexemes.Left_paren:
        sentinel = viuact.lexemes.Right_paren
        tag = viuact.lexemes.Paren_tag(token = tokens[i - 1].tok())
        # g = [Element(tag)]
    elif sentinel.t() is viuact.lexemes.Left_curly:
        sentinel = viuact.lexemes.Right_curly
        tag = viuact.lexemes.Curly_tag(token = tokens[i - 1].tok())
        g = [Element(tag)]
    else:
        raise viuact.errors.Invalid_sentinel(tokens[i - 1].tok().at(), str(sentinel))
    sentinels.push(sentinel)

    while i < len(tokens):
        each = tokens[i]
        if each.t() in (viuact.lexemes.Left_paren, viuact.lexemes.Left_curly,):
            i, gp = group_one(tokens, i + 1, each, sentinels)
            g.append(gp)
            continue

        if each.t() in (
            viuact.lexemes.Right_paren, viuact.lexemes.Right_curly,) and each.t() is not sentinel:
            raise viuact.errors.Unbalanced_braces(
                each.tok().at(),
                each,
            ).note('expected {}'.format(repr(
                '}' if sentinels.top() is viuact.lexemes.Right_curly else ')'
            )))

        i += 1
        if each.t() is sentinel:
            sentinels.pop(each)
            break

        g.append(Element(each))

    return i, Group(g, tag)

def group(tokens):
    groups = []

    i = 0
    while i < len(tokens):
        s = Sentinels()
        i, g = group_one(tokens, i + 1, tokens[i], s)
        if not s.empty():
            raise viuact.errors.Unbalanced_braces(
                s.popped().tok().at(),
                s.popped(),
            ).note('expected {}'.format(repr(
                '}' if sentinels.top() is viuact.lexemes.Right_curly else ')'
            )))
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
        if type(each) is Element and each.t() is viuact.lexemes.Labelled_name:
            tok = viuact.lexemes.Token(
                pos = (each.val().tok().at()[0], each.val().tok().at()[1] + 1),
                text = str(each.val().tok())[1:],
            )
            args.append(viuact.forms.Argument_bind(
                name = each.val(),
                value = viuact.forms.Name_ref(name = viuact.lexemes.Name(tok)),
            ))
        else:
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

def parse_argument_bind(group):
    return viuact.forms.Argument_bind(
        name = group[0].val(),
        value = parse_expr(group[1]),
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
        if group.lead().t() is viuact.lexemes.Labelled_name:
            return parse_argument_bind(group)
        if group.lead().t() is viuact.lexemes.If:
            return viuact.forms.If(
                guard = parse_expr(group[1]),
                if_true = parse_expr(group[2]),
                if_false = parse_expr(group[3]),
            )
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

        if name.t() is viuact.lexemes.Name:
            return viuact.forms.Named_parameter(name)
        else:
            return viuact.forms.Labelled_parameter(name)

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

def parse_type(group):
    if type(group) is Element:
        return viuact.forms.Type_name(
            name = group.val(),
            template_parameters = [],
        )
    if type(group) is Group and len(group) == 2:
        return viuact.forms.Type_name(
            name = group[1].val(),
            template_parameters = [parse_type(each) for each in group[0]],
        )
    raise None

def parse_val_fn(group):
    offset = (0 if len(group) == 4 else 1)
    template_parameters = (group[offset + 0] if offset else [])
    name = group[offset + 1]
    parameter_list = group[offset + 2]
    return_type = group[offset + 3]

    fmt = 'type of {}: ({}) -> {}'
    if template_parameters:
        fmt += ' [with {}]'
    viuact.util.log.note(fmt.format(
        str(name.val()),
        ', '.join(map(lambda a: str(a.val()), parameter_list)),
        str(return_type.val()),
        ', '.join(map(lambda a: str(a.val()), template_parameters)),
    ))

    return viuact.forms.Val_fn_spec(
        name = name,
        template_parameters = template_parameters,
        parameter_types = list(map(parse_type, parameter_list)),
        return_type = parse_type(return_type),
    )

def parse_val_var(group):
    template_params = []
    name = None
    parameter_list = None
    return_type = None
    raise None

def parse_val(group):
    is_var = 4
    is_fn = 5

    # The first element is not a list of type parameters so let's reduce the
    # length requirements.
    if type(group[1]) is Element:
        is_var -= 1
        is_fn -= 1

    if len(group) == is_var:
        return parse_val_var(group)
    if len(group) == is_fn:
        return parse_val_fn(group)
    raise None

def parse_enum(group):
    pass

def parse_impl(groups):
    forms = []

    for g in groups:
        if g.lead().t() is viuact.lexemes.Let and len(g) == 4:
            forms.append(parse_fn(g))
        elif g.lead().t() is viuact.lexemes.Val:
            forms.append(parse_val(g))
        elif g.lead().t() is viuact.lexemes.Enum:
            forms.append(parse_enum(g))
        else:
            tok = g.lead().val().tok()
            raise viuact.errors.Unexpected_token(tok.at(), str(tok))

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
