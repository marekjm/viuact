template_parameters = (
    "'a",
    "'b",
    "'c",
    "'d",
)


class Type:
    class t:
        def __init__(self, name, parameters = ()):
            self._name = name               # str
            self._parameters = parameters   # [Type]

        def __eq__(self, other):
            if not isinstance(other, Type.t):
                raise TypeError('cannot compare type with {}'.format(typeof(other)))
            n = (str(self.name()) == str(other.name()))
            p = (self.parameters() == other.parameters())
            return (n and p)

        def __str__(self):
            if self._parameters:
                return '(({}) {})'.format(
                    ' '.join(map(str, self.parameters())),
                    str(self.name()),
                )
            else:
                return str(self.name())

        def __repr__(self):
            return str(self)

        def name(self):
            return self._name

        def parameters(self):
            return self._parameters

        def polymorphic_base(self):
            return self.name().startswith("'")

        def polymorphic(self):
            p = any(map(lambda x: x.polymorphic(), self.parameters()))
            return (self.polymorphic_base() or p)

        def merge(self, other):
            raise None

        def match(self, other, template_parameters):
            tp = template_parameters

            if self.polymorphic() and tp[self.name()] is None:
                tp[self.name()] = other
                return True, tp

            if self.polymorphic() and tp[self.name()] is not None:
                return tp[self.name()].match(other, template_parameters)

            if self.name() != other.name():
                return False, tp

            for i, pair in zip(self.parameters(), other.parameters()):
                a, b = pair
                ok, _ = a.match(b, tp)
                if not ok:
                    return False, tp

            return True, tp

    class any(t):
        def __init__(self):
            super().__init__('any')

        def __eq__(self):
            return True

        def match(self, other, template_parameters):
            return True

    class i8(t):
        def __init__(self):
            super().__init__('i8')

    class i16(t):
        def __init__(self):
            super().__init__('i16')

    class i32(t):
        def __init__(self):
            super().__init__('i32')

    class i64(t):
        def __init__(self):
            super().__init__('i64')

    class u8(t):
        def __init__(self):
            super().__init__('u8')

    class u16(t):
        def __init__(self):
            super().__init__('u16')

    class u32(t):
        def __init__(self):
            super().__init__('u32')

    class u64(t):
        def __init__(self):
            super().__init__('u64')

    class string(t):
        def __init__(self):
            super().__init__('string')


class Signature:
    def __init__(self, parameters, return_type, template_parameters):
        self._parameters = parameters
        self._return = return_type
        self._template_parameters = template_parameters

def make_sig(fn, parameters, return_type, template_parameters):
    return Signature(
        parameters,
        return_type,
        template_parameters,
    )


class Type_error(Exception):
    pass

class Cannot_unify(Type_error):
    pass


class State:
    def __init__(self, template_parameters):
        self._template_parameters = {
            k : None for k in template_parameters
        }
        self._slots = {}

    def validate_type(self, t):
        return t

    def _unify_base(self, a, other):
        if a.polymorphic_base() and not other.polymorphic_base():
            v = self._template_parameters[str(a)]
            if (v is not None) and v != other:
                raise Cannot_unify(a, other)
            elif (v is not None) and v == other:
                pass
            else:
                self._template_parameters[str(a)] = other
            return (a, other,)
        return None

    def _unify_with_a(self, a, other):
        if a.polymorphic_base() and not other.polymorphic_base():
            v = self._template_parameters[str(a)]
            if (v is not None) and v != other:
                raise Cannot_unify(a, other)
            elif (v is not None) and v == other:
                pass
            else:
                self._template_parameters[str(a)] = other
            return (a, other,)
        elif (not a.polymorphic_base()) and other.polymorphic_base():
            v = self._template_parameters[str(other)]
            if (v is not None) and v != a:
                raise Cannot_unify(a, other)
            elif (v is not None) and v == a:
                pass
            else:
                if str(other).startswith("'_~"):
                    self._template_parameters[str(other)] = a
                    tp = {}
                    for k, v in self._template_parameters.items():
                        if k == str(other):
                            continue
                        if v is None:
                            tp[k] = v
                        elif v == other:
                            tp[k] = a
                        else:
                            tp[k] = v
                    self._template_parameters = tp
                else:
                    self._template_parameters[str(other)] = a
            return (a, other,)

        if a.name() != other.name():
            raise Cannot_unify(a, other)

        for of_a, of_other in zip(a.qualified_parameters(),
                other.qualified_parameters()):
            self.unify_types(of_a, of_other)

        return (a, other,)

    def unify_types(self, a, b):
        print('unifying: {} == {}'.format(a, b))

        if a == b:
            return (a, b,)
        if (not a.polymorphic()) and (not b.polymorphic()):
            raise Cannot_unify(a, b)  # two different non-polymorphic types
        if a.polymorphic_base() and b.polymorphic_base():
            ax = self._template_parameters[a.name()]
            bx = self._template_parameters[b.name()]
            if (ax is None) and (bx is not None):
                self._template_parameters[a.name()] = bx
            elif (ax is not None) and (bx is None):
                self._template_parameters[b.name()] = ax
            else:
                # Two different core-polymorphic types cannot be unified because
                # there is not enough information to produce a more concrete
                # type.
                placeholders = list(filter(lambda _: _.startswith("'_~"),
                        self._template_parameters.keys()))
                pt = 0
                if placeholders:
                    pt = max(map(lambda _: int(_.rsplit('~', 1)[1]),
                        placeholders)) + 1
                pt = Type.t(name = "'_~{}".format(pt))
                self._template_parameters[str(pt)] = None
                self._template_parameters[str(a)] = pt
                self._template_parameters[str(b)] = pt
                # raise Cannot_unify(a, b)
            return (a, b,)

        try:
            return self._unify_with_a(a, b)
        except Cannot_unify:
            raise Cannot_unify(a, b)

    def _store_type_parameters(self, t):
        ps = []
        for each in t.parameters():
            if each.polymorphic_base():
                n = 0
                candidate = '{}~{}'.format(str(each), n)
                if candidate in self._template_parameters:
                    pat = '{}~'.format(str(each))
                    n = map(lambda x: int(x.rsplit('~', 1)[1]),
                        filter(lambda x: x.startswith(pat),
                        self._template_parameters.keys()))
                    if not n:
                        n = 0
                    else:
                        n = max(n) + 1
                    candidate = '{}~{}'.format(str(each), n)
                self._template_parameters[candidate] = None
                ps.append(Type.t('{}~{}'.format(str(each), n)))
            elif each.polymorphic():
                ps.append(self._store_type_parameters(each))
            else:
                # No reason to process a type that is not polymorphic.
                ps.append(each)
        return Type.t(name = t.name(), parameters = tuple(ps))

    def store(self, slot, t):
        if t.polymorphic():
            t = self._store_type_parameters(t)
        self._slots[slot] = t

    def load(self, slot):
        return self._slots[slot]

    def erase(self, slot):
        del self._slots[slot]

    def _stringify_type(self, t):
        s = ''

        if t.polymorphic_base():
            tx = self._template_parameters[str(t)]
            if tx is None:
                tx = str(t)
            else:
                tx = self._stringify_type(tx)
            s = '{}'.format(tx)
        elif t.polymorphic():
            ps = []
            for each in t.parameters():
                ps.append(self._stringify_type(each))
            s = '(({}) {})'.format(
                ' '.join(ps),
                t.name(),
            )
        else:
            s = str(t)

        return s

    def dump(self):
        print('template parameters:')
        for k, v in self._template_parameters.items():
            print('  {} => {}'.format(k, v))
        print('slots:')
        for k, v in self._slots.items():
            s = '  {} => {}'.format(k, v)
            if v.polymorphic():
                s += ' [{}]'.format(self._stringify_type(v))
            print(s)


st = State(template_parameters = (
    "'a",
))
st.store('a', Type.t('map', (
    Type.t("'key"),
    Type.t("'value"),
)))
st.dump()
st.unify_types(
    Type.t("'key~0"),
    Type.t("'a"),
)
st.dump()
st.unify_types(
    Type.i8(),
    Type.t("'_~0"),
)
st.dump()
