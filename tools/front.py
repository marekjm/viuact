#!/usr/bin/env python3

import datetime
import os
import re
import shutil
import sys

import viuact.util.help


HELP = '''{NAME}
    {executable} - Viuact language tools

{SYNOPSIS}
    {exec_tool} <%fg(man_const)tool%r> [%arg(option)...] [%arg(arg)]
    {exec_blank} --version
    {exec_blank} --help
    {exec_blank} --env
    {exec_blank} cc     --mode %fg(man_var)MODE%r %arg(file).vt
    {exec_blank} opt    %arg(file).asm
    {exec_blank} fmt    %arg(file).vt
    {exec_blank} switch [<%fg(man_const)tool%r>] [%arg(option)...] [%arg(arg)]

{DESCRIPTION}
    %text
    This executable is a front for tooling supplied for the Viuact langauge. It
    can be used as a driver for those other tools (compiler, linker, formatter).
    Each tool can be used on its own without this wrapper.

    %text
    This is also an executable that can be used to inspect state of the Viuact
    installation on a system by checking paths, environment variables' values,
    etc.

{TOOLS}

    %fg(man_se)cc%r %arg(file).vt
        Compile modules and executables.

    %fg(man_se)opt%r %arg(file).asm
        Output modules and executables.

    %fg(man_se)fmt%r %arg(file).vt
        Format Viuact source code.

    %fg(man_se)switch%r
        %text
        Manage multiple Viua environments.

{OPTIONS}
    %opt(--help)
        Display this message.

    %opt(--version)
        Display version information.

    %opt(--env)
        %text
        Display information about the environment that the compiler will use.

{EXAMPLES}
    %text
    Some examples to give you a taste of how to use this program.

    %fg(man_se)THE CANONICAL PROGRAM%r

        %text
        Here's how you would go about compiling the canonical "Hello, World!"
        program:

            %fg(white)$ cat hello.lisp
            %fg(white)(let main () (print "Hello, World!"))
            %fg(white)$ viuact cc --mode exec hello.lisp
            %fg(white)$ viuact opt build/_default/hello.asm
            %fg(white)$ viua-vm build/_default/hello.bc
            %fg(white)Hello, World!

        Quite simple.

    %fg(man_se)CREATING NEW SWITCH%r

        %text
        The following command will create a switch named %fg(man_var)foo%r if it
        does not already exist:

            %fg(white)$ viuact switch create foo
            %fg(white)$ viuact switch ls
            %fg(white)   foo

        %text
        Use %fg(man_se)viuact switch ls%r to get a list of all created switches.

    %fg(man_se)ACTIVATING A SWITCH (SWITCHING TO A SWITCH)%r

        %text
        The following command will activate a switch named %fg(man_var)foo%r:

            %fg(white)$ `viuact switch to foo`
            %fg(white)$ viuact switch ls
            %fg(white)*  foo

        %text
        The backquotes are necessary to make your shell execute the exports
        required to make the switch work. Note how a star appears before the
        name of the active switch.

    %fg(man_se)ACTIVATING A SWITCH ON SHELL INITIALISATION (ZSH)%r

        %text
        Add the following line to your %fg(man_const)~/.zshrc%r file:

            %fg(white). ~/.local/viuact/switch/init/init.zsh \\
            %fg(white)    >/dev/null 2>/dev/null || true

        %text
        This will activate a default switch (if any) during ZSH initialisation.

        %text
        You can set a default switch using the following command:

            %fg(white)$ viuact switch to --set foo
            %fg(white)$ viuact switch ls
            %fg(white) = foo

        %text
        The = character appearing before switch's name means that it is set as
        the default one.

{COPYRIGHT}
    %copyright(2020) Marek Marecki

    This is Free Software published under GNU GPL v3 license.
'''


EXECUTABLE = 'viuact'


CORE_TOOLS = (
    'cc',
    'opt',
    'fmt',
    'switch',
)
KNOWN_TOOLS = (
    *CORE_TOOLS,
    'exec',
)

DEFAULT_CORE_DIR = '.'
CORE_DIR = os.environ.get('VIUACT_CORE_DIR', DEFAULT_CORE_DIR)
def get_core_exec_path(executable):
    is_development = (CORE_DIR == '.')
    return os.path.join(os.path.expanduser(CORE_DIR), {
        'cc': ('tools/cc.py' if is_development else 'viuact-cc'),
        'fmt': ('tools/format.py' if is_development else 'viuact-format'),
        'opt': ('tools/opt.py' if is_development else 'viuact-opt'),
        'switch': ('tools/switch.py' if is_development else 'viuact-switch'),
    }.get(executable))

def main(executable_name, args):
    arg = (args[0] or '--help')
    tool = None

    if arg == '--version':
        print('{} version {} ({})'.format(
            EXECUTABLE,
            viuact.__version__,
            viuact.__commit__,
        ))
        if '--verbose' in args:
            print('code fingerprint: {}'.format(
                viuact.__code__,
            ))
    elif arg == '--help':
        viuact.util.help.print_help(
            EXECUTABLE,
            suite = viuact.suite,
            version = viuact.__version__,
            text = HELP,
        )
    elif arg == '--env':
        print('VIUACT_CORE_DIR: {}'.format(
            os.environ.get('VIUACT_CORE_DIR', '(none)'),
        ))
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
        print('VIUA_LIBRARY_PATH: {}'.format(
            '\n'.join(map(lambda each: (
                '{}{}'.format(
                    (' ' * (len('VIUA_LIBRARY_PATH') + 2)),
                    each,
                )),
                os.environ.get('VIUA_LIBRARY_PATH').split(':'))).strip(),
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

    if tool in CORE_TOOLS:
        executable_path = get_core_exec_path(tool)
        argv = (executable_path, *args[1:],)
        os.execvp(executable_path, argv)
    else:
        sys.stderr.write('warning: tool not implemented\n')
        exit(1)

    exit(0)

main(sys.argv[0], sys.argv[1:])
