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


class Lexer_error(Error):
    pass

class Unexpected_character(Lexer_error):
    def __init__(self, pos, s):
        super().__init__(pos)
        self.bad = s

    def what(self):
        return '{}: {}'.format(super().what(), repr(self.bad))
