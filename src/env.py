import os

DEFAULT_OUTPUT_DIRECTORY = os.environ.get('VIUAC_OUTPUT_DIRECTORY', './build/_default')

VIUAC_LIBRARY_PATH = (
    tuple(filter(lambda each: each.strip(),
        os.environ.get('VIUAC_LIBRARY_PATH', '').split(':')
    ))
    + (DEFAULT_OUTPUT_DIRECTORY,)
)

VIUA_ASM_PATH = os.environ.get('VIUA_ASM_PATH', '../core/viuavm/build/bin/vm/asm')


def bool_of_string(s):
    return (s.lower() in ('1', 'true', 'yes',))

VIUAC_VERBOSE = bool_of_string(os.environ.get('VIUAC_VERBOSE', ''))
VIUAC_DEBUGGING = bool_of_string(os.environ.get('VIUAC_DEBUGGING', ''))
VIUAC_INFO = bool_of_string(os.environ.get('VIUAC_INFO', ''))
