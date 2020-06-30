import viuact.errors
import viuact.lexemes
import viuact.forms


def strip_comments(tokens):
    return list(filter(
        lambda each: each.t() is not viuact.lexemes.Comment, tokens))


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
    def __init__(self, value):
        self._value = value

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
    if sentinel.t() is viuact.lexemes.Left_paren:
        sentinel = viuact.lexemes.Right_paren
        # g = [Element(viuact.lexemes.Paren_tag(token = tokens[i - 1].tok()))]
        g = []
    elif sentinel.t() is viuact.lexemes.Left_curly:
        sentinel = viuact.lexemes.Right_curly
        g = [Element(viuact.lexemes.Curly_tag(token = tokens[i - 1].tok()))]

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

    return i, Group(g)

def group(tokens):
    groups = []

    i = 0
    while i < len(tokens):
        i, g = group_one(tokens, i + 1, [ tokens[i], ])
        groups.append(g)

    return groups


def parse_fn_parameter(group):
    if type(group) is Element:
        name = group.val()
        if name.t() not in (viuact.lexemes.Name, viuact.lexemes.Labelled_name,):
            raise viuact.errors.Unexpected_token(
                pos = name.tok().at(),
                s = str(name),
            ).note('expected a name or a labelled name')

        return viuact.forms.Named_parameter(name)

    raise viuact.errors.Unexpected_token(
        pos = group.lead().lead().tok().at(),
        s = str(group.lead().lead()),
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
            print('a let function')
            forms.append(parse_fn(g))

    return forms

def parse(tokens):
    no_comments = strip_comments(tokens)
    groups = group(no_comments)
    print('groups:', len(groups))
    for i, each in enumerate(groups):
        print(i, '---- >8 ----')
        for x in each:
            print('   ', x)
        print('---- 8< ----')
    return parse_impl(groups)


def to_data(forms):
    return forms
    # data = []
    # return { 'forms': data, }
