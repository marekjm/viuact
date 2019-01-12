import os

DEFAULT_OUTPUT_DIRECTORY = os.environ.get('VIUAC_OUTPUT_DIRECTORY', './build/_default')
STDLIB_HEADERS_DIRECTORY = os.environ.get('VIUAC_STDLIB_HEADERS', './stdlib')


class Required_environment_variable_not_set(Exception):
    pass
class Misconfigured_environment_variable(Exception):
    pass


if os.environ.get('VIUA_LIBRARY_PATH') is None:
    raise Required_environment_variable_not_set('VIUA_LIBRARY_PATH')


VIUAC_LIBRARY_PATH = tuple(filter(os.path.isdir, (
    tuple(filter(lambda each: each.strip(),
        os.environ.get('VIUAC_LIBRARY_PATH', '').split(':')
    ))
    + (DEFAULT_OUTPUT_DIRECTORY,)
    + (STDLIB_HEADERS_DIRECTORY,)
)))
if (not VIUAC_LIBRARY_PATH) and os.environ.get('VIUAC_LIBRARY_PATH') is None:
    raise Required_environment_variable_not_set('VIUAC_LIBRARY_PATH')
if (not VIUAC_LIBRARY_PATH) and os.environ.get('VIUAC_LIBRARY_PATH') is not None:
    raise Misconfigured_environment_variable('VIUAC_LIBRARY_PATH')


VIUA_ASM_PATH = os.environ.get('VIUA_ASM_PATH', '../core/viuavm/build/bin/vm/asm')
if (not os.path.isfile(VIUA_ASM_PATH)) and os.environ.get('VIUA_ASM_PATH') is None:
    raise Required_environment_variable_not_set('VIUA_ASM_PATH')
if (not os.path.isfile(VIUA_ASM_PATH)) and os.environ.get('VIUA_ASM_PATH') is not None:
    raise Misconfigured_environment_variable('VIUA_ASM_PATH')


def bool_of_string(s):
    return (s.lower() in ('1', 'true', 'yes',))

VIUAC_VERBOSE = bool_of_string(os.environ.get('VIUAC_VERBOSE', ''))
VIUAC_DEBUGGING = bool_of_string(os.environ.get('VIUAC_DEBUGGING', ''))
VIUAC_INFO = bool_of_string(os.environ.get('VIUAC_INFO', ''))

class Dump_intermediate:
    Tokens = 'tokens'
    Groups = 'groups'
    Expressions = 'exprs'

VIUAC_DUMP_INTERMEDIATE = list(
    filter(lambda each: each in (
        Dump_intermediate.Tokens,
        Dump_intermediate.Groups,
        Dump_intermediate.Expressions,
    ),
    os.environ.get('VIUAC_DUMP_INTERMEDIATE', '').split(','),
))
