import sys

import viuact.util.colors


def raw(*args):
    sys.stderr.write('{}\n'.format(' '.join(map(str, args))))

def make_prefix(kind, path, pos):
    if path is not None and type(path) is not str:
        raise Exception('invalid path: {}: {}'.format(
            str(type(path))[8:-2], path))
    if pos is not None and type(pos) is not tuple and len(pos) != 2:
        raise Exception('invalid position: {}: {}'.format(
            str(type(path))[8:-2], path))

    kinds = {
        'error': 'red',
        'debug': 'green',
        'warning': 'orange_red_1',
        'note': 'cyan',
        'fixme': 'yellow',
    }

    prefix = ''
    if path is not None:
        prefix = viuact.util.colors.colorise('white', path)
    if pos is not None:
        prefix = '{}:{}:{}'.format(
            prefix,
            *pos,
        )

    if kind is not None:
        colored_kind = viuact.util.colors.colorise(kinds[kind], kind)
        if prefix:
            prefix = '{}: {}'.format(prefix, colored_kind)
        else:
            prefix = colored_kind

    return prefix

def error(s, path = None, pos = None):
    sys.stderr.write('{}: {}\n'.format(
        make_prefix('error', path, pos),
        s,
    ))

def debug(s, path = None, pos = None):
    sys.stderr.write('{}: {}\n'.format(
        make_prefix('debug', path, pos),
        s,
    ))

def note(s, path = None, pos = None):
    sys.stderr.write('{}: {}\n'.format(
        make_prefix('note', path, pos),
        s,
    ))

def fixme(s, path = None, pos = None):
    sys.stderr.write('{}: {}\n'.format(
        make_prefix('fixme', path, pos),
        s,
    ))

def warning(s, path = None, pos = None):
    sys.stderr.write('{}: {}\n'.format(
        make_prefix('warning', path, pos),
        s,
    ))

def print(s, path = None, pos = None):
    p = make_prefix(None, path, pos)
    sys.stderr.write('{}\n'.format(
        '{}: {}'.format(p, s)
        if p else
        '{}'.format(s)
    ))
