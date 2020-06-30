import sys

import viuact.util.colors


def make_prefix(kind, path, pos):
    if path is not None and type(path) is not str:
        raise Exception('invalid path: {}: {}'.format(
            str(type(path))[8:-2], path))
    if pos is not None and type(pos) is not tuple and len(pos) != 2:
        raise Exception('invalid position: {}: {}'.format(
            str(type(path))[8:-2], path))

    kinds = {
        'error': 'red',
        'note': 'cyan',
    }

    prefix = ''
    if path is not None:
        prefix = viuact.util.colors.colorise('white', path)
    if pos is not None:
        prefix = '{}:{}:{}'.format(
            prefix,
            *pos,
        )

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

def note(s, path = None, pos = None):
    sys.stderr.write('{}: {}\n'.format(
        make_prefix('note', path, pos),
        s,
    ))
