#!/usr/bin/env python3


class Template:
    def __init__(self, name):
        if type(name) is not str:
            raise TypeError('cannot use {} as name of template variable'.format(
                type(name),
            ))
        if not name:
            raise ValueError('name of template variable cannot be empty')
        if name[0] == "'":
            raise ValueError(
                'name of template variable cannot start with the \' character')
        self._name = name

    def __repr__(self):
        return '(template: [{}])'.format(self.to_string())

    def __eq__(self, other):
        if isinstance(other, Base):
            return False
        if type(other) is not Template:
            raise TypeError('cannot compare <template> with {}'.format(
                type(other),
            ))
        return (other.name() == self.name())

    def __hash__(self):
        return hash(self.name())

    def to_string(self):
        return self.name()

    def name(self, human_readable = False):
        s = "'{}".format(self._name)
        if human_readable:
            s = s.split('~', maxsplit = 1)[0]
        return s

    def polymorphic(self):
        return True

    def concretise(self, blueprint):
        return blueprint[self]

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
class Base:
    def __init__(self, templates = ()):
        if not all(map(lambda _: (type(_) in (Template, Value, Fn,)),
            templates)):
            raise TypeError('invalid template variable list: {}'.format(
                templates,))
        self._templates = templates

    def __eq__(self, other):
        return (self.to_string() == other.to_string())

    def to_string(self):
        raise TypeError('{} type cannot be stringified'.format(type(self)))

    def templates(self):
        return self._templates

    def polymorphic(self):
        return any(map(lambda _: _.polymorphic(), self.templates()))

    def cast_from(self, t):
        return False


class Void(Base):
    def __init__(self, templates = ()):
        super().__init__(templates)

    def __repr__(self):
        return self.to_string()

    def to_string(self):
        if self.templates():
            return '(({}) void)'.format(
                ' '.join(list(map(lambda _: _.to_string(), self.templates()))),
                self.name(),
            )
        else:
            return self.name()

    def name(self):
        return 'void'

    def polymorphic(self):
        return super().polymorphic()

    def cast_from(self, _):
        return True

    def concretise(self, blueprint):
        return Void(
            templates = tuple(map(
                lambda _: _.concretise(blueprint),
                self.templates(),
            )),
        )


# Value types are used to describe values like integers, vectors, and
# enumerations. They have a name (eg. i8) and an optional list of templates by
# which the type is parametrised.
class Value(Base):
    def __init__(self, name, templates = ()):
        super().__init__(templates)
        if type(name) is not str:
            raise TypeError('cannot use {} as name of value type'.format(
                type(name),
            ))
        if not name:
            raise TypeError('name of value type cannot be empty')
        if name[0] == "'":
            raise ValueError(
                'name of type cannot start with the \' character')
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
        return Value(
            name = self.name(),
            templates = tuple(map(
                lambda _: _.concretise(blueprint),
                self.templates(),
            )),
        )


class Pointer(Base):
    def __init__(self, to):
        super().__init__(())
        self._to = to

    def __repr__(self):
        return '(pointer: [{}])'.format(self._to.to_string())

    def to_string(self):
        return '*{}'.format(self._to.to_string())

    def name(self):
        return 'pointer'

    def to(self):
        return self._to


# Function types are used to describe functions. They do not have a name and are
# described by the types of their formal parameters and return type.
class Fn(Base):
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
        return Fn(
            rt = rt,
            pt = pt,
            templates = tuple(set(self.templates()) - set(blueprint.keys())),
        )
