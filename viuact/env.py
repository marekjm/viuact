import os


LIBRARY_PATH = '/opt/lib/viuact:/usr/local/lib/viuact:/usr/lib/viuact'


def library_path():
    v = os.environ.get('VIUACT_LIBRARY_PATH')
    if v:
        return '{}:{}'.format(v, LIBRARY_PATH)
    else:
        return LIBRARY_PATH
