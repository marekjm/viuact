import os

DEFAULT_OUTPUT_DIRECTORY = os.environ.get('VIUAC_OUTPUT_DIRECTORY', './build/_default')

VIUAC_LIBRARY_PATH = (
    tuple(filter(lambda each: each.strip(),
        os.environ.get('VIUAC_LIBRARY_PATH', '').split(':')
    ))
    + (DEFAULT_OUTPUT_DIRECTORY,)
)

VIUA_ASM_PATH = os.environ.get('VIUA_ASM_PATH', '../core/viuavm/build/bin/vm/asm')
