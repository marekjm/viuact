try:
    import colored
except ImportError:
    colored = None

def colorise(color, s):
    if (colored is None) or (color is None):
        return s
    return '{}{}{}'.format(
        colored.fg(color),
        s,
        colored.attr('reset'),
    )

def colorise_wrap(color, s):
    return "‘{}’".format(colorise(color, s))

def colorise_repr(color, s):
    r = repr(s)
    return "‘{}’".format(colorise(color, r[1:-1]))
