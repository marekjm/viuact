import os


class Environment_error(Exception):
    pass

class Undefined_environment_variable(Environment_error):
    pass


LIBRARY_PATH = '/opt/lib/viuact:/usr/local/lib/viuact:/usr/lib/viuact'


def library_path():
    v = os.environ.get('VIUACT_LIBRARY_PATH')
    if v:
        return '{}:{}'.format(v, LIBRARY_PATH)
    else:
        return LIBRARY_PATH

def core_directory(default = None):
    v = os.environ.get('VIUACT_CORE_DIR', default)
    if v is None:
        raise Undefined_environment_variable('VIUACT_CORE_DIR')
    return v

def output_directory(default = 'build/_default'):
    return os.environ.get('VIUACT_OUTPUT_DIR', default)

# Variables to consider:
#
#   VIUACT_STDLIB_HEADERS_DIR
#       Interface files for Viuact standard library (this includes interface
#       files to Viua standard library). Single directory.
#
#   VIUA_LIBRARY_PATH
#       Where to find Viua VM bytecode modules. Multiple directories.
#
#   VIUA_ASM_EXEC, VIUA_VM_EXEC
#       Path to viua-asm or viua-vm executable to use. Useful for switches.
#
#   VIUA_ASM_FLAGS
#       A list of additional flags to include when invoking viua-asm.
