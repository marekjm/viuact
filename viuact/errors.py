class Error(Exception):
    def __init__(self, pos):
        self.line = pos[0]
        self.character = pos[1]
        self._fallout = []
        self._notes = []

    def at(self, human = False):
        return (self.line + int(human), self.character + int(human),)

    def then(self, another_error):
        self._fallout = another_error
        return self

    def what(self):
        return ' '.join(str(type(self))[8:-2].split('.')[-1].lower().split('_'))

    def notes(self):
        return self._notes

    def note(self, s):
        self._notes.append(s)
        return self


class Info(Error):
    def __init__(self, pos, m):
        super().__init__(pos)
        self.bad = m

    def what(self):
        return self.bad


class Fail(Error):
    def __init__(self, pos, m):
        super().__init__(pos)
        self.bad = m

    def what(self):
        return self.bad


class Lexer_error(Error):
    pass

class Unexpected_character(Lexer_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), repr(self.bad))


class Parser_error(Error):
    pass

class Unexpected_token(Lexer_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), repr(self.bad))

class Unbalanced_braces(Lexer_error):
    def __init__(self, pos, s = None):
        super().__init__(pos)
        self.bad = s

    def what(self):
        s = super().what()
        if self.bad is not None:
            s = '{}: unexpected {}'.format(s, repr(str(self.bad)))
        return s

class Invalid_sentinel(Lexer_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), repr(self.bad))


class Emitter_error(Error):
    pass

class Source_cannot_be_void(Emitter_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{} for {}'.format(super().what(), self.bad)

class Invalid_arity(Emitter_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{} of function {}'.format(super().what(), self.bad)

class Unknown_function(Emitter_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), self.bad)

class Missing_argument(Emitter_error):
    def __init__(self, pos, fn, arg):
        super().__init__(pos)
        self.fn = fn
        self.arg = arg

    def what(self):
        return '{} for function {}: {}'.format(super().what(), self.fn, self.arg)

class Missing_positional_argument(Missing_argument):
    pass

class Missing_labelled_argument(Missing_argument):
    pass

class No_signature_for_function(Emitter_error):
    def __init__(self, pos, fn):
        super().__init__(pos)
        self.fn = fn

    def what(self):
        return '{} {}'.format(super().what(), self.fn)

class Type_error(Emitter_error):
    pass

class Type_mismatch(Type_error):
    def __init__(self, pos, a, b):
        super().__init__(pos)
        self.a = a
        self.b = b

    def what(self):
        return '{}: {} != {}'.format(super().what(), self.a, self.b)

class Bad_returned_type(Type_error):
    def __init__(self, pos, fn, declared, returned):
        super().__init__(pos)
        self.fn = fn
        self.declared = declared
        self.returned = returned

    def what(self):
        return '{w} from {fn}: returned {ret} != declared {decl}'.format(
            w = super().what(),
            fn = self.fn,
            decl = self.declared,
            ret = self.returned,
        )
