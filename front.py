#!/usr/bin/env python3

import datetime
import os
import shutil
import sys

import viuact
import viuact.frontend
import viuact.driver
import viuact.env


HELP = '''{man_executable}(1)

NAME
    {executable} - Viuact language tools

SYNOPSIS
    {executable} --version
    {exec_blank} --help
    {exec_blank} --env
    {exec_blank} <tool> [<option>...] [<operand>...]

DESCRIPTION
    This executable is a front for tooling supplied for the Viuact langauge. It
    can be used as a driver for those other tools (compiler, linker, formatter).
    Each tool can be used on its own without this wrapper.

    This is also an executable that can be used to inspect state of the Viuact
    installation on a system by checking paths, environment variables' values,
    etc.

OPTIONS
    --help
        Display this message.

    --version
        Display version information.

    --env
        Display information about the environment that the compiler will use.

TOOLS

    cc
        Compile modules and executables.

    link
        Link modules and executables.

    fmt
        Format Viuact source code.

    switch
        Create and manage semi-isolated Viua environments (switches).

EXAMPLES

    Some examples to give you a taste of how to use this program.

    THE CANONICAL PROGRAM

        Here's how you would go about compiling the canonical "Hello, World!"
        program:

            $ cat hello.lisp
            (let main () (print "Hello, World!"))
            $ viuact cc --mode exec hello.lisp
            $ viuact opt build/_default/hello.asm
            $ viua-vm build/_default/hello.bc
            Hello, World!

        Quite simple.

    CREATING NEW SWITCH

            $ viuact switch make foo
            $ viuact switch ls
             foo

        This command will create a new switch named "foo".

    ACTIVATING A SWITCH (SWITCHING TO A SWITCH)

            $ `viuact switch to foo`
            $ viuact switch ls
            *foo

        The backquotes are necessary to make your shell execute the exports
        required to make the switch work. Note how a star appears before the
        name of the active switch.

SEE ALSO
    viuact-cc(1)
    viuact-opt(1)
    viuact-format(1)

COPYRIGHT
    Copyright (c) 2020 Marek Marecki

    This is Free Software published under GNU GPL v3 license.
'''

EXECUTABLE = 'viuact'

def print_help(executable, stream = None):
    stream = (stream if stream is not None else sys.stdout)
    stream.write(HELP.format(
        executable = executable,
        man_executable = executable.upper(),
        exec_blank = (' ' * len(executable)),
    ))


KNOWN_TOOLS = (
    'cc',
    'link',
    'fmt',
    'exec',
    'switch',
)

class Env_switch:
    def __init__(self, path):
        self.path = path

    @staticmethod
    def root_path(safe = True):
        DEFAULT_SWITCH_ROOT = '~/.local/viuact/switch'
        return os.path.expanduser(
            os.environ.get('VIUACT_SWITCH_ROOT', DEFAULT_SWITCH_ROOT))

    @staticmethod
    def switches_path():
        return os.path.join(Env_switch.root_path(), 'here')

    @staticmethod
    def available_switches():
        return os.listdir(Env_switch.switches_path())

    @staticmethod
    def exists(switch_name):
        return (switch_name in Env_switch.available_switches())

    @staticmethod
    def path_of(switch_name):
        return os.path.join(Env_switch.switches_path(), switch_name)

    @staticmethod
    def get_active():
        return os.environ.get('VIUACT_SWITCH')

    @staticmethod
    def is_active(switch_name):
        return (switch_name == Env_switch.get_active())

def item_or(seq, n, default = None):
    return (seq[n] if n < len(seq) else default)

def main(executable_name, args):
    arg = (args[0] or '--help')
    tool = None

    if arg == '--version':
        print('{} version {} ({})'.format(
            EXECUTABLE,
            viuact.__version__,
            viuact.__commit__,
        ))
    elif arg == '--help':
        print_help(EXECUTABLE)
    elif arg == '--env':
        print('DEFAULT_OUTPUT_DIRECTORY: {}'.format(
            viuact.env.DEFAULT_OUTPUT_DIRECTORY,
        ))
        print('STDLIB_HEADERS_DIRECTORY: {}'.format(
            viuact.env.STDLIB_HEADERS_DIRECTORY,
        ))
        if viuact.env.VIUACT_LIBRARY_PATH:
            prefix = 'VIUACT_LIBRARY_PATH:'
            print('{} {}'.format(
                prefix,
                viuact.env.VIUACT_LIBRARY_PATH[0],
            ))
            for each in viuact.env.VIUACT_LIBRARY_PATH[1:]:
                print('{} {}'.format(
                    (len(prefix) * ' '),
                    each,
                ))
        print('VIUA_ASM_PATH: {}'.format(
            viuact.env.VIUA_ASM_PATH,
        ))
        if viuact.env.VIUACT_ASM_FLAGS:
            prefix = 'VIUACT_ASM_FLAGS:'
            print('{} {}'.format(
                prefix,
                viuact.env.VIUACT_ASM_FLAGS[0],
            ))
            for each in viuact.env.VIUACT_ASM_FLAGS[1:]:
                print('{} {}'.format(
                    (len(prefix) * ' '),
                    each,
                ))
        if viuact.env.VIUACT_DUMP_INTERMEDIATE:
            prefix = 'VIUACT_DUMP_INTERMEDIATE:'
            print('{} {}'.format(
                prefix,
                viuact.env.VIUACT_DUMP_INTERMEDIATE[0],
            ))
            for each in viuact.env.VIUACT_DUMP_INTERMEDIATE[1:]:
                print('{} {}'.format(
                    (len(prefix) * ' '),
                    each,
                ))
    elif arg.startswith('--'):
        sys.stderr.write('error: unknown option: {}\n'.format(arg))
        exit(1)
    elif arg not in KNOWN_TOOLS:
        sys.stderr.write('error: unknown tool: {}\n'.format(repr(arg)))
        exit(1)
    else:
        tool = arg

    if tool is None:
        exit(0)

    if tool == 'cc':
        os.execvp('viuact-cc', args)
    elif tool == 'link':
        os.execvp('viuact-opt', args)
    elif tool == 'fmt':
        os.execvp('viuact-format', args)
    elif tool == 'exec':
        pass
    elif tool == 'switch':
        switch_tool = item_or(args, 1, 'status')
        if switch_tool == 'status':
            switch_name = Env_switch.get_active()
            if switch_name is None:
                sys.stderr.write('error: no active switch\n')
                exit(1)
            print('switch: {}'.format(switch_name))
            print('path:   {}'.format(os.path.join(Env_switch.switches_path(),
                switch_name)))
        elif switch_tool == 'make':
            switch_name = item_or(args, 2)
            if switch_name is None:
                sys.stderr.write(
                    'error: name for a new switch is required\n')
                exit(1)
            switch_root = Env_switch.switches_path()
            if not os.path.isdir(switch_root):
                print('info: creating root switch directory: {}'.format(
                    switch_root))
                os.makedirs(switch_root)
            switch_path = os.path.join(switch_root, switch_name)
            if os.path.isdir(switch_path):
                sys.stderr.write('error: switch {} already exists, overwriting\n'.format(
                    switch_name))
                exit(1)

            os.makedirs(switch_path)
            print('new switch in: {}'.format(switch_path))

            SWITCH_DIRS = (
                'bin',
                'lib/viuact',
            )
            for each in SWITCH_DIRS:
                os.makedirs(os.path.join(switch_path, each))

            BASE_BIN_DIR = os.path.expanduser('~/.local/bin')
            SWITCH_BIN_DIR = os.path.join(switch_path, 'bin')
            SWITCH_EXECUTABLES = (
                'viuact-cc',
                'viuact-opt',
                'viuact-format',
                'viua-vm',
                'viua-asm',
                'viua-dis',
            )
            for each in SWITCH_EXECUTABLES:
                os.link(
                    os.path.join(BASE_BIN_DIR, each),
                    os.path.join(SWITCH_BIN_DIR, each),
                )

            with open(os.path.join(switch_path, '.meta'), 'w') as ofstream:
                ofstream.write(''.join(map(lambda x: '{}: {}\n'.format(*x), {
                    'date_created':
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'switch_root': switch_root,
                    'switch_name': switch_name,
                    'viuact_version': '{} ({})'.format(
                        viuact.__version__,
                        viuact.__commit__,
                    ),
                }.items())))
        elif switch_tool == 'rm':
            switch_name = item_or(args, 2)
            if switch_name is None:
                sys.stderr.write(
                    'error: name of a switch is required\n')
                exit(1)
            switch_root = Env_switch.switches_path()
            switch_path = os.path.join(switch_root, switch_name)
            if os.path.isdir(switch_path):
                shutil.rmtree(switch_path, ignore_errors = True)
        elif switch_tool == 'ls':
            try:
                for switch_name in sorted(Env_switch.available_switches()):
                    print('{}{}'.format(
                        ('*' if Env_switch.is_active(switch_name) else ' '),
                        switch_name,
                    ))
            except FileNotFoundError:
                sys.stderr.write('error: switch directory does not exist\n')
                exit(1)
        elif switch_tool == 'to':
            switch_name = item_or(args, 2)

            if switch_name is None:
                sys.stderr.write('error: no switch name to switch to\n')
                exit(1)
            if not Env_switch.exists(switch_name):
                sys.stderr.write(
                    'error: switch does not exist: {}\n'.format(switch_name))
                exit(1)

            switch_path = Env_switch.path_of(switch_name)
            print(''.join(map(lambda x: 'export {}={}\n'.format(*x), {
                'VIUACT_SWITCH': switch_name,
                'PATH': '{sw}/bin:{env}'.format(
                    sw = switch_path,
                    env = os.environ.get('PATH')
                ),
                'VIUA_LIBRARY_PATH': '{sw}/lib/viua:{sw}/lib/viuact:{env}'.format(
                    sw = switch_path,
                    env = os.environ.get('PATH'),
                ),
            }.items())), end = '')
        else:
            sys.stderr.write(
                'error: unknown switch subcommand: {}\n'.format(switch_tool))
            exit(1)

main(sys.argv[0], sys.argv[1:])
