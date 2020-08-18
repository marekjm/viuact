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

        # Initialise the variable to "no type" as the compiler did not yet infer
        # what type it represents.
        state['variables'][registered_name] = None

        # Strip the initial ' character from the name (it will be added by the
        # template class anyway).
        return template(name = registered_name[1:])
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
def unify(mapping, left, right):
    raise Cannot_unify(left, right)

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
if True:
    state = { 'indexes': {}, 'variables': {}, }
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
        u = unify({}, l, r)
    except Cannot_unify as e:
        left, right = e.args
        sys.stderr.write('cannot unify: {} != {}\n'.format(
            left.to_string(),
            right.to_string(),
        ))

if True:
    i8 = value('i8')
    a = template('a')
    try_unify({}, i8, a)
