#!/usr/bin/env python3

import sys

# This class is the basis of the type hierarchy. It encapsulates the basic fact
# that a type may be polymorphic and have some template parameters (a.k.a.
# templates).
#
# From this base type, which is not that useful on its own, we build two more
# type-types:
#
#   - a "value type" which is used to describe values like integers, strings,
#     vectors, enums, etc.
#   - a "function type" which is used to describe functions
#
class template:
    def __init__(self, name):
        if type(name) is not str:
            raise TypeError('cannot use {} as name of template variable'.format(
                type(name),
            ))
        self._name = name

    def __repr__(self):
        return '(template: [{}])'.format(self.to_string())

    def __eq__(self, other):
        if type(other) is not template:
            raise TypeError('cannot compare <template> with {}'.format(
                type(other),
            ))
        return (other.name() == self.name())

    def __hash__(self):
        return hash(self.name())

    def to_string(self):
        return self.name()

    def name(self):
        return "'{}".format(self._name)

    def polymorphic(self):
        return True

    def concretise(self, blueprint):
        return blueprint[self]

class base:
    def __init__(self, templates = ()):
        if not all(map(lambda _: (type(_) in (template, value,)),
            templates)):
            raise TypeError('invalid template variable list: {}'.format(
                templates,))
        self._templates = templates

    def to_string(self):
        raise TypeError('{} type cannot be stringified'.format(type(self)))

    def templates(self):
        return self._templates

    def polymorphic(self):
        return any(map(lambda _: _.polymorphic(), self.templates()))


# Value types are used to describe values like integers, vectors, and
# enumerations. They have a name (eg. i8) and an optional list of templates by
# which the type is parametrised.
class value(base):
    def __init__(self, name, templates = ()):
        super().__init__(templates)
        if type(name) is not str:
            raise TypeError('cannot use {} as name of value type'.format(
                type(name),
            ))
        self._name = name

    def __repr__(self):
        return '(value: [{}])'.format(self.to_string())

    def to_string(self):
        if self.templates():
            return '(({}) {})'.format(
                ' '.join(list(map(lambda _: _.to_string(), self.templates()))),
                self.name(),
            )
        else:
            return self.name()

    def name(self):
        return self._name

    def polymorphic(self):
        return (super().polymorphic() or self._name.startswith("'"))

    def concretise(self, blueprint):
        return value(
            name = self.name(),
            templates = tuple(map(
                lambda _: _.concretise(blueprint),
                self.templates(),
            )),
        )


# Function types are used to describe functions. They do not have a name and are
# described by the types of their formal parameters and return type.
class fn(base):
    def __init__(self, rt, pt = (), templates = ()):
        super().__init__(templates)
        self._return_type = rt
        self._parameter_types = pt

    def to_string(self):
        map_to_string = lambda seq: map(lambda _: _.to_string(), seq)
        if self.templates():
            return '(({}) ({}) -> {})'.format(
                ' '.join(list(map_to_string(self.templates()))),
                ' '.join(list(map_to_string(self.parameter_types()))),
                self.return_type().to_string(),
            )
        else:
            return '(({}) -> {})'.format(
                ' '.join(list(map_to_string(self.parameter_types()))),
                self.return_type().to_string(),
            )

    def return_type(self):
        return self._return_type

    def parameter_types(self):
        return self._parameter_types

    def concretise(self, blueprint):
        rt = self.return_type().concretise(blueprint)
        pt = tuple(map(
            lambda _: _.concretise(blueprint),
            self.parameter_types(),
        ))
        return fn(
            rt = rt,
            pt = pt,
            templates = tuple(set(self.templates()) - set(blueprint.keys())),
        )


def register_type(state, t):
    if type(t) is template:
        # We have to initialise the index for this name if was not seen before.
        # This is needed because we can declare more than one value description
        # with the same template name, eg.:
        #
        #   (val ('a) id ('a) -> 'a)
        #   (val ('a) sort ((('a) vec)) -> (('a) vec))
        #
        # but they should not be considered the same. So, for each usage of a
        # template let's rename it to {name}~{index} (the language forbids
        # forming such names from user code so there is no risk of conflict).
        name = t.name()
        if name not in state['indexes']:
            state['indexes'][name] = 0
        index = state['indexes'][name]
        registered_name = '{}~{}'.format(name, index)

        # Remember to update the index for the next occurence of this template
        # name. Every index must be unique.
        state['indexes'][name] += 1

        # Strip the initial ' character from the name (it will be added by the
        # template class anyway).
        t = template(name = registered_name[1:])

        # Initialise the variable to "no type" as the compiler did not yet infer
        # what type it represents.
        state['variables'][t] = None

        return t
    elif type(t) is value:
        # If the type describes a value we just have to register its templates,
        # and replace the original ones with the registered variant.
        registered_templates = []
        for each in t.templates():
            registered_templates.append(register_type(state, each))

        return value(
            name = t.name(),
            templates = tuple(registered_templates),
        )
    elif type(t) is fn:
        # registered_return_type = register_type(state, t.return_type())
        # registered_parameter_types = ()
        registered_templates = []
        blueprint = {}
        for each in t.templates():
            tr = register_type(state, each)
            blueprint[each] = tr
            registered_templates.append(tr)

        registered_return_type = t.return_type().concretise(
            blueprint = blueprint,
        )
        registered_parameter_types = [
            each.concretise(blueprint = blueprint)
            for each
            in t.parameter_types()
        ]

        return fn(
            rt = registered_return_type,
            pt = registered_parameter_types,
            templates = tuple(registered_templates),
        )

    raise None


# Type unification answers an important question that the compiler asks while
# processing the source code: is type A the same as B? The below function
# answers the question with a new type - C, that both A and B match. If such a
# type cannot be found it throws an exception.
class Cannot_unify(Exception):
    pass
def unify_impl(state, left, right):
    print('unify_impl({} + {})'.format(left.to_string(), right.to_string()))

    # This switcharoo allows the code to make the assumption that a combination
    # of a non-template type with a template type, the right parameter is the
    # non-template one. In effect, it prevents duplicating the checks and makes
    # the code shorter.
    if type(left) is not template and type(right) is template:
        return unify(state, right, left)

    if type(left) is template and type(right) is template:
        left_none = (state['variables'][left] is None)
        right_none = (state['variables'][right] is None)
        if left_none and right_none:
            t = register_type(state, template('_'))
            state['variables'][left] = t
            state['variables'][right] = t
            return t
        if (not left_none) and right_none:
            t = state['variables'][left]
            state['variables'][right] = t
            return t
        if left_none and (not right_none):
            t = state['variables'][right]
            state['variables'][left] = t
            return t
        if (not left_none) and (not right_none):
            l = state['variables'][left]
            r = state['variables'][right]
            return unify_impl(state, l, r)

    if type(left) is template and type(right) is not template:
        if state['variables'][left] is None:
            t = right
            state['variables'][left] = t
            return t
        return unify_impl(state, state['variables'][left], right)

    if type(left) is not template and type(right) is not template:
        # Function type will never unify with value type.
        if type(left) is not type(right):
            raise Cannot_unify(left, right)

        # If both concrete types are equal there is nothing to do, so let's just
        # return the left one.
        if left == right:
            return left

        # Try to unify value types if their names match, since we have a nominal
        # type system (working with names) instead of a structural one (working
        # with "shapes", ie. comparing members instead of names).
        if type(left) is value and (left.name() == right.name()):
            lt = left.templates()
            rt = right.templates()
            if len(lt) != len(rt):
                # Types with the same name but different lengths of templates
                # are really a compiler error since it should not allow such a
                # situation to happen.
                #
                # We cannot have, for example, (('a) vec) and (('a 'b) vec)
                # values in the same program.
                raise Cannot_unify(left, right)

            ut = []
            for l, r in zip(left.templates(), right.templates()):
                ut.append(unify_impl(state, l, r))
            return value(
                name = left.name(),
                templates = tuple(ut),
            )

    raise Cannot_unify(left, right)
def unify(state, left, right):
    try:
        return unify_impl(state, left, right)
    except Cannot_unify as e:
        l, r = e.args
        raise Cannot_unify((left, l,), (right, r,))

################################################################################
# Type stringification and concretisation.
#
if True:
    i8 = value('i8')
    i64 = value('i64')
    print(i8.to_string(), i8.polymorphic())

    vec = value('vec', templates = (template('a'),))
    print(vec.to_string(), vec.polymorphic())

    fa = fn(rt = i8)
    print(fa.to_string(), fa.polymorphic())

    fb = fn(rt = i8, pt = (i8,))
    print(fb.to_string(), fb.polymorphic())

    fc = fn(rt = i64, pt = (template('a'),), templates = (template('a'),))
    print(fc.to_string(), fc.polymorphic())

    # A sort function could have such a type.
    fs = fn(
        rt = value('vec', templates = (template('a'),)),
        pt = (value('vec', templates = (template('a'),)),),
        templates = (template('a'),),
    )
    print(fs.to_string(), fs.polymorphic())

    fsa = fs.concretise(blueprint = {
        template('a'): i8,
    })
    print(fsa.to_string(), fsa.polymorphic())
    print('=' * 80)

################################################################################
# Type registration
#
def make_typing_state():
    return { 'indexes': {}, 'variables': {}, }
if True:
    state = make_typing_state()
    a = template('a')
    ar = register_type(state, a)
    print(a.to_string(), '=>', ar.to_string())

    vec = value('vec', templates = (a,))
    vecr = register_type(state, vec)
    print(vec.to_string(), '=>', vecr.to_string())

    b = template('b')
    f = fn(
        rt = value('vec', templates = (b,)),
        pt = (
            value('vec', templates = (b,)),
            b,
        ),
        templates = (b,),
    )
    fr = register_type(state, f)
    print(f.to_string(), '=>\n    ', fr.to_string())
    print('=' * 80)

################################################################################
# Type unification
#
def try_unify(state, l, r):
    try:
        u = unify(state, l, r)
        print('{} + {} => {} (in {})'.format(
            l.to_string(),
            r.to_string(),
            u.to_string(),
            state['variables'],
        ))
        return u
    except Cannot_unify as e:
        (left, l,), (right, r,) = e.args
        sys.stderr.write('cannot unify: {} [{}] != {} [{}] (in {})\n'.format(
            left.to_string(),
            l.to_string(),
            right.to_string(),
            r.to_string(),
            state['variables'],
        ))

if False:
    state = make_typing_state()
    i8 = value('i8')
    i64 = value('i64')
    a = register_type(state, template('a'))
    b = register_type(state, template('b'))
    try_unify(state, a, b)
    try_unify(state, a, i8)
    try_unify(state, b, i8)

if True:
    state = make_typing_state()
    i8 = value('i8')
    i64 = value('i64')
    a = register_type(state, template('a'))
    b = register_type(state, template('b'))
    v = register_type(state, value('vec', templates = (template('a'),)))
    try_unify(state, a, v)
    try_unify(state, template('a~1'), b)
    try_unify(state, v, register_type(state, value('vec', templates = (i8,))))
    try_unify(state, i8, b)
    # try_unify(state, b, i8)
    # try_unify(state, b, i64)
