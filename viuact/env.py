import os


DEFAULT_OUTPUT_DIRECTORY = os.environ.get('VIUACT_OUTPUT_DIRECTORY', './build/_default')
STDLIB_HEADERS_DIRECTORY = os.environ.get('VIUACT_STDLIB_HEADERS', './stdlib')


VIUACT_LIBRARY_PATH = tuple(filter(os.path.isdir, (
    tuple(filter(lambda each: each.strip(),
        os.environ.get('VIUACT_LIBRARY_PATH', '').split(':')
    ))
    + (DEFAULT_OUTPUT_DIRECTORY,)
    + (STDLIB_HEADERS_DIRECTORY,)
)))


def bool_of_string(s):
    return (s.lower() in ('1', 'true', 'yes',))

VIUACT_VERBOSE = bool_of_string(os.environ.get('VIUACT_VERBOSE', ''))
VIUACT_DEBUGGING = bool_of_string(os.environ.get('VIUACT_DEBUGGING', ''))
VIUACT_INFO = bool_of_string(os.environ.get('VIUACT_INFO', ''))


class Dump_intermediate:
    Tokens = 'tokens'
    Groups = 'groups'
    Expressions = 'exprs'

VIUACT_DUMP_INTERMEDIATE = list(
    filter(lambda each: each in (
        Dump_intermediate.Tokens,
        Dump_intermediate.Groups,
        Dump_intermediate.Expressions,
    ),
    os.environ.get('VIUACT_DUMP_INTERMEDIATE', '').split(','),
))


VIUA_ASM_PATH = os.environ.get('VIUA_ASM_PATH', 'viua-asm')
VIUACT_ASM_FLAGS = tuple(os.environ.get('VIUACT_ASM_FLAGS', '').split())
