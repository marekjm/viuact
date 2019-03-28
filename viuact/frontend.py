import sys


from viuact import driver


def print_error(s):
    text = '{}\n'.format(s)
    return sys.stderr.write(text)

HELP = '''{man_executable}(1)

NAME

    {executable} - Viuact compiler

SYNOPSIS

    {executable} <file>
    {exec_blank} --mode (module | exec | auto) <file>
    {exec_blank} --help

DESCRIPTION

    Compiler from Viuact to Viua VM assembly language. Viuact is a
    high-level programming language with a Lisp-like syntax.

OPTIONS

    --help      - display this message
    --mode module | exec | auto
                - set compilation mode; 'auto' is the default one
'''

def print_help(executable_name):
    print(HELP.format(
        man_executable = executable_name.upper(),
        executable = executable_name,
        exec_blank = (' ' * len(executable_name)),
    ).strip())

def cc(executable_name, args):
    if '--help' in args:
        print_help(executable_name)
        exit(0)

    if not args or len(args) not in (1, 3):
        print_error('error: invalid number of operands: expected 1 or 3')
        print_error('note: syntax: {} <file>'.format(executable_name))
        print_error('              {} --mode {} <file>'.format(
            executable_name,
            Compilation_mode.Automatic,
        ))
        print_error('              {} --mode {} <file>'.format(
            executable_name,
            Compilation_mode.Executable,
        ))
        print_error('              {} --mode {} <file>'.format(
            executable_name,
            Compilation_mode.Module,
        ))
        exit(1)

    compile_as = driver.Compilation_mode.Automatic
    source_file = None
    if len(args) == 1:
        source_file = args[0]
    else:
        if args[0] != '--mode':
            print_error('error: unknown option: {}'.format(repr(args[0])))
            print_error('note: run {} --help to get help'.format(executable_name))
            exit(1)

        compile_as = args[1]
        source_file = args[2]

    if compile_as not in driver.Valid_compilation_modes:
        print_error('error: invalid compilation mode: {}'.format(compile_as))
        exit(1)

    return {
        'executable_name': executable_name,
        'args': args,
        'source_file': source_file,
        'compile_as': compile_as,
    }

def opt(args):
    return {
        'main_source_file': args[0],
        'main_output_file': (args[1] if len(args) >= 2 else None),
    }
