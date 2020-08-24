#!/usr/bin/env python3


import viuact.util.log
from viuact.util.type_annotations import T, I, Alt
import viuact.typesystem.t


class State:
    def __init__(self):
        # Indexes for template variables. Every time a templated type is
        # registered, for example:
        #
        #       (('a) foo)
        #
        # It is registered as (('a~X) foo) where the X is an index of the
        # template variable; the index being a counter of how many types the
        # same name was used.
        #
        # Why do we needed it? Because we want to allow different templates to
        # reuse template variables names, eg.:
        #
        #       (val ('a) fn ('a) -> i64)
        #       (enum ('a) option (None (Some 'a)))
        #
        # but still need to distinguish between them, ie. not all 'a variables
        # are the same type.
        self._indexes = {}

        # Template variables mapping template names to types or templates. For
        # example, the template variable 'a may be mapped to:
        #
        #   - None: if no type was inferred for this template variable and it is
        #     completely free
        #   - template variable: if a constraint was inferred for this template
        #     variable and it must share a type with some other template
        #     variable
        #   - template variable: if a type was inferred for this template
        #     variable, but it is another template variable
        #   - type: if a concrete type was inferred for this template variable
        #   - value: if a simple value was inferred for this template variable
        #
        # Template variables' names are a single "'" character (an apostrophe)
        # followed by: a normal name (for ordinary template variables, ie. those
        # created by user code), an underscore (for template variables
        # synthesised by the compiler).
        self._variables = {}

        # Named slots with types. A generic store for variable-type mapping for
        # the user language. The key is a variable name; the value is either a
        # state-variable (ie. valid key in the _variables table), or a type.
        self._slots = {}

    def register_type(self, t):
        if type(t) is viuact.typesystem.t.Template:
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
            if name not in self._indexes:
                self._indexes[name] = 0
            index = self._indexes[name]
            registered_name = '{}~{}'.format(name, index)

            # Remember to update the index for the next occurence of this template
            # name. Every index must be unique.
            self._indexes[name] += 1

            # Strip the initial ' character from the name (it will be added by the
            # template class anyway).
            t = viuact.typesystem.t.Template(name = registered_name[1:])

            # Initialise the variable to "no type" as the compiler did not yet infer
            # what type it represents.
            self._variables[t] = None

            return t
        elif type(t) is viuact.typesystem.t.Value:
            # If the type describes a value we just have to register its templates,
            # and replace the original ones with the registered variant.
            registered_templates = []
            for each in t.templates():
                registered_templates.append(self.register_type(each))

            return viuact.typesystem.t.Value(
                name = t.name(),
                templates = tuple(registered_templates),
            )
        elif type(t) is viuact.typesystem.t.Fn:
            # registered_return_type = register_type(state, t.return_type())
            # registered_parameter_types = ()
            registered_templates = []
            blueprint = {}
            for each in t.templates():
                tr = self.register_type(each)
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

            return viuact.typesystem.t.Fn(
                rt = registered_return_type,
                pt = tuple(registered_parameter_types),
                templates = tuple(registered_templates),
            )

        raise None

    def is_unknown(self, x):
        return (self._variables[x] is None)

    def variable(self, x):
        return self._variables[x]

    def let(self, x, value):
        self._variables[x] = value
        return value

    def store(self, key, t):
        t = Alt(
            I(viuact.typesystem.t.Base),
            T(viuact.typesystem.t.Template),
        ) | t
        self._slots[key] = t
        return t

    def load(self, key):
        return self._slots[key]

    def erase(self, key):
        del self._slots[key]

    def stringify_type(self, t, human_readable = False):
        if type(t) is viuact.typesystem.t.Template:
            if self.is_unknown(t):
                return t.name(human_readable)
            else:
                return self.stringify_type(self.variable(t), human_readable)
        elif type(t) is viuact.typesystem.t.Value:
            ts = [self.stringify_type(each, human_readable) for each in t.templates()]
            if ts:
                return '(({}) {})'.format(
                    ' '.join(ts),
                    t.name(),
                )
            else:
                return t.name()
        elif type(t) is viuact.typesystem.t.Fn:
            pts = [self.stringify_type(each) for each in t.parameter_types()]
            rt = self.stringify_type(t.return_type())
            return '(({}) -> {})'.format(
                ' '.join(pts),
                rt,
            )
        raise TypeError(t)

    def dump(self):
        viuact.util.log.raw('template variables:')
        for k, v in self._variables.items():
            viuact.util.log.raw('  {} => {}'.format(k, v))

        viuact.util.log.raw('slots:')
        for k, v in self._slots.items():
            viuact.util.log.raw('  {} => {}'.format(
                k,
                self.stringify_type(v),
            ))


# Type unification answers an important question that the compiler asks while
# processing the source code: is type A the same as B? The below function
# answers the question with a new type - C, that both A and B match. If such a
# type cannot be found it throws an exception.
class Cannot_unify(Exception):
    pass
def unify_impl(state, left, right):
    viuact.util.log.raw('unifying: {} == {}'.format(left, right))

    # This switcharoo allows the code to make the assumption that a combination
    # of a non-template type with a template type, the right parameter is the
    # non-template one. In effect, it prevents duplicating the checks and makes
    # the code shorter.
    if type(left) is not viuact.typesystem.t.Template and type(right) is viuact.typesystem.t.Template:
        return unify(state, right, left)

    if type(left) is viuact.typesystem.t.Template and type(right) is viuact.typesystem.t.Template:
        if left == right:
            return left

        left_none = state.is_unknown(left)
        right_none = state.is_unknown(right)
        if left_none and right_none:
            t = state.register_type(viuact.typesystem.t.Template('_'))
            state.let(left, t)
            state.let(right, t)
            return t
        if (not left_none) and right_none:
            return state.let(right, state.variable(left))
        if left_none and (not right_none):
            return state.let(left, state.variable(right))
        if (not left_none) and (not right_none):
            l = state.variable(left)
            r = state.variable(right)
            return unify_impl(state, l, r)

    if type(left) is viuact.typesystem.t.Template and type(right) is not viuact.typesystem.t.Template:
        if state.is_unknown(left):
            return state.let(left, right)
        return unify_impl(state, state.variable(left), right)

    if type(left) is not viuact.typesystem.t.Template and type(right) is not viuact.typesystem.t.Template:
        # All types can be unified with void, but being unified with a void
        # means they stop existing, ie. they cannot be used to create new
        # values.
        left_void = (type(left) is viuact.typesystem.t.Void)
        right_void = (type(right) is viuact.typesystem.t.Void)
        if left_void or right_void:
            return viuact.typesystem.t.Void()

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
        if type(left) is viuact.typesystem.t.Value and (left.name() == right.name()):
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
            for l, r in zip(lt, rt):
                ut.append(unify_impl(state, l, r))
            return viuact.typesystem.t.Value(
                name = left.name(),
                templates = tuple(ut),
            )

        if type(left) is viuact.typesystem.t.Fn:
            # lt = left.templates()
            # rt = right.templates()
            # if len(lt) != len(rt):
            #     # See comment about template list lengths in value-type
            #     # unification code.
            #     raise Cannot_unify(left, right)

            lp = left.parameter_types()
            rp = right.parameter_types()
            if len(lp) != len(rp):
                # See comment about template list lengths in value-type
                # unification code.
                raise Cannot_unify(left, right)

            # ut = []
            # for l, r in zip(lt, rt):
            #     ut.append(unify_impl(state, l, r))

            up = []
            for l, r in zip(lp, rp):
                up.append(unify_impl(state, l, r))

            lr = left.return_type()
            rr = right.return_type()
            ur = unify_impl(state, lr, rr)

            return fn(
                rt = rr,
                pt = tuple(up),
                # templates = tuple(ut),
            )

    raise Cannot_unify(left, right)
def unify(state, left, right):
    try:
        t = unify_impl(state, left, right)
        viuact.util.log.raw('unifying: {} == {}'.format(left, right))
        viuact.util.log.raw('unified: {}'.format(t))
        return t
    except Cannot_unify as e:
        l, r = e.args
        raise Cannot_unify((left, l,), (right, r,))
