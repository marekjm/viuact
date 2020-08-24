class Typing_pred:
    pass

class T(Typing_pred):
    @staticmethod
    def typeof_type(value):
        return str(value)[8:-2]

    def typeof_value(value):
        return T.typeof_type(type(value))

    def __init__(self, t):
        self._type = t

    def match(self, value):
        if type(value) is not self._type:
            raise TypeError('actual <{}> is not declared <{}>'.format(
                T.typeof_value(value),
                T.typeof_type(self._type),
            ))
        return value

    def __contains__(self, value):
        return self.match(value)

    def __or__(self, value):
        return self.match(value)

class I(Typing_pred):
    def __init__(self, t):
        self._type = t

    def match(self, value):
        if not isinstance(value, self._type):
            raise TypeError('actual <{}> is not declared <{}>'.format(
                T.typeof_value(value),
                T.typeof_type(self._type),
            ))
        return value

    def __contains__(self, value):
        return self.match(value)

    def __or__(self, value):
        return self.match(value)

class Alt(Typing_pred):
    def __init__(self, *c):
        self._conditions = c

    def try_match(self, pred, value):
        try:
            (pred | value)
        except TypeError:
            return False
        return True

    def match(self, value):
        if any(map(lambda pred: self.try_match(pred, value),
            self._conditions)):
            return value
        else:
            raise TypeError('actual <{}> is not declared ...'.format(
                T.typeof_value(value),
            ))

    def __contains__(self, value):
        return self.match(value)

    def __or__(self, value):
        return self.match(value)
