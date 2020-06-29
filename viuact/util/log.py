import sys

import viuact.util.colors

def error(s, path = None, pos = None):
    if path is not None and type(path) is not str:
        raise Exception('invalid path: {}: {}'.format(
            str(type(path))[8:-2], path))
    if pos is not None and type(pos) is not tuple and len(pos) != 2:
        raise Exception('invalid position: {}: {}'.format(
            str(type(path))[8:-2], path))

    prefix = viuact.util.colors.colorise('red', 'error')
    if path is not None:
        prefix = '{}:{}'.format(
            prefix,
            viuact.util.colors.colorise('white', path),
        )
    if pos is not None:
        prefix = '{}:{}:{}'.format(
            prefix,
            *pos,
        )

    sys.stderr.write('{}: {}\n'.format(
        prefix,
        s,
    ))
