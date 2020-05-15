#!/usr/bin/env python3

import datetime
import os
import re
import shutil
import sys

try:
    import colored
except ImportError:
    colored = None

import viuact
import viuact.frontend
import viuact.driver
import viuact.env


HELP = '''{man_exec}{man_pad_left}{man_title}{man_pad_right}{man_exec}

{NAME}
    {executable} - Viuact language tools

{SYNOPSIS}
    {executable} --version
    {exec_blank} --help
    {exec_blank} --env
    {exec_blank} <tool> [<option>...] [<operand>...]

{DESCRIPTION}
    This executable is a front for tooling supplied for the Viuact langauge. It
    can be used as a driver for those other tools (compiler, linker, formatter).
    Each tool can be used on its own without this wrapper.

    This is also an executable that can be used to inspect state of the Viuact
    installation on a system by checking paths, environment variables' values,
    etc.

{OPTIONS}
    --help
        Display this message.

    --version
        Display version information.

    --env
        Display information about the environment that the compiler will use.

{TOOLS}

    cc
        Compile modules and executables.

    link
        Link modules and executables.

    fmt
        Format Viuact source code.

    switch
        Create and manage semi-isolated Viua environments (switches).

{EXAMPLES}

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

{SEE_ALSO}
    viuact-cc(1)
    viuact-opt(1)
    viuact-format(1)

{COPYRIGHT}
    Copyright (c) 2020 Marek Marecki

    This is Free Software published under GNU GPL v3 license.


{suite} {version}{bottom_pad}{man_exec}
'''

HELP_SWITCH = '''{man_exec}{man_pad_left}{man_title}{man_pad_right}{man_exec}

{NAME}
    {executable} - Manage multiple language versions

{SYNOPSIS}
    {executable_ex} {cmd_ex} [{opt_ex}]... [{arg_ex}]

    {exec_tool} --help
    {exec_blank} create [{opt_ex}] {arg_ex}
    {exec_blank} if     [{opt_ex}] {arg_ex}
    {exec_blank} init
    {exec_blank} ls     [{opt_ex}]
    {exec_blank} rm     {arg_ex}
    {exec_blank} show   [{opt_ex}...]
    {exec_blank} to     [{opt_ex}...] [{arg_ex}]

{DESCRIPTION}
    This executable is a front for tooling supplied for the Viuact langauge. It
    can be used as a driver for those other tools (compiler, linker, formatter).
    Each tool can be used on its own without this wrapper.

    This is also an executable that can be used to inspect state of the Viuact
    installation on a system by checking paths, environment variables' values,
    etc.

{COMMANDS}
    If no command is given, the default is %fg(man_se)show%r.

    %fg(man_se)create%r %fg(man_ex)name%r
        Create new switch named %fg(man_ex)name%r.

    %fg(man_se)if%r %fg(man_ex)name%r
        Check if %fg(man_ex)name%r is the active switch. Prints %fg(steel_blue_3)true%r to
        standard output if swith %fg(man_ex)name%r is active; %fg(steel_blue_3)false%r otherwise.
        Always exit with 0.

        %fg(man_ex)-e%r
            Instead of printing to standard output use exit code to signal the
            result of the operation. Exit with %fg(steel_blue_3)0%r if switch %fg(man_ex)name%r is active;
            %fg(steel_blue_3)1%r otherwise.

    %fg(man_se)init%r
        Initialise switch root directory. This command needs to be executed
        before any other %fg(man_se)viuact switch%r command.

    %fg(man_se)ls%r
        List created switches. Active switch is prepended with * and its name is
        displayed %fg(green)green%r. Default switch is prepended with = and its
        name is displayed %fg(red)red%r.

        %fg(man_ex)-s%r
            Do not prepend markers to switch names and disable coloring.

    %fg(man_se)rm%r %fg(man_ex)name%r
        Remove switch named %fg(man_ex)name%r.

    %fg(man_se)show%r
        Show active switch. If the %fg(man_ex)--default%r option is given then
        show the default switch. The %fg(man_ex)--verbose%r option may be used
        to get information about the active switch.

        %fg(man_ex)--verbose%r
            Show information about the active switch instead of just its name.

        %fg(man_ex)--default%r
            Use default switch instead of the active one.

    %fg(man_se)to%r %fg(man_ex)name%r
        Emit shell script required to activate a switch named %fg(man_ex)name%r.
        Use `%fg(man_se)viuact switch to %fg(man_ex)foo%r` to activate a switch
        named %fg(man_ex)foo%r. Use %fg(man_ex)--set%r option to also set the
        switch as default.

        %fg(man_ex)--set%r
            Set the switch %fg(man_ex)name%r as default in addition to emitting
            the activating commands.

        %fg(man_ex)--default%r
            Activate the default switch.

{OPTIONS}
    %fg(man_se)--help%r
        Display this message.

{SEE_ALSO}
    viuact-cc(1)
    viuact-opt(1)
    viuact-format(1)

{COPYRIGHT}
    Copyright (c) 2020 Marek Marecki

    This is Free Software published under GNU GPL v3 license.


{suite} {version}{bottom_pad}{man_exec}
'''

EXECUTABLE = 'viuact'
SUITE = 'Viuact'

def print_help(executable, stream = None, text = None):
    stream = (stream if stream is not None else sys.stdout)

    COLUMN_COUNT = 80

    man_title = 'Viuact Manual'
    man_executable = '{}(1)'.format(executable.upper())

    man_padding_left = ((COLUMN_COUNT - len(man_title)) // 2)
    man_padding_left -= len(man_executable)

    man_padding_right = COLUMN_COUNT
    man_padding_right -= len(man_title)
    man_padding_right -= man_padding_left
    man_padding_right -= (2 * len(man_executable))

    version_string = viuact.__version__
    bottom_padding = (COLUMN_COUNT - 1)
    bottom_padding -= len(SUITE)
    bottom_padding -= len(version_string)
    bottom_padding -= len(man_executable)

    MAN_SECTION_COLOR = 'light_red'
    MAN_EX_COLOR = 'green_3b'

    text = (text or HELP)

    fg = re.compile(r'%fg\(([a-z][a-z_]+(?:_[1-4][ab]?)?)\)')
    attr_reset = re.compile(r'%r\b')
    colorings = re.findall(fg, text)

    def map_color(color):
        mapped = {
            'man_ex': MAN_EX_COLOR,
            'man_se': MAN_SECTION_COLOR,
        }.get(color, color)
        return mapped

    for color in colorings:
        text = text.replace(
            '%fg({})'.format(color),
            (colored.fg(map_color(color)) if colored else ''))
    text = re.sub(attr_reset, (colored.attr('reset') if colored else ''), text)

    stream.write((text or HELP).format(
        executable = executable,
        exec_tool = executable.replace('-', ' '),
        exec_blank = (' ' * len(executable)),

        man_exec = man_executable,
        man_title = man_title,
        man_pad_left = (' ' * man_padding_left),
        man_pad_right = (' ' * man_padding_right),

        executable_ex = colorise(
            MAN_SECTION_COLOR, executable.replace('-', ' ')),
        cmd_ex = colorise(MAN_EX_COLOR, 'COMMAND'),
        arg_ex = colorise(MAN_EX_COLOR, 'ARG'),
        opt_ex = colorise(MAN_EX_COLOR, 'OPTION'),

        suite = SUITE,
        version = version_string,
        bottom_pad = (' ' * bottom_padding),

        NAME = colorise(MAN_SECTION_COLOR, 'NAME'),
        SYNOPSIS = colorise(MAN_SECTION_COLOR, 'SYNOPSIS'),
        DESCRIPTION = colorise(MAN_SECTION_COLOR, 'DESCRIPTION'),
        COMMANDS = colorise(MAN_SECTION_COLOR, 'COMMANDS'),
        OPTIONS = colorise(MAN_SECTION_COLOR, 'OPTIONS'),
        TOOLS = colorise(MAN_SECTION_COLOR, 'TOOLS'),
        EXAMPLES = colorise(MAN_SECTION_COLOR, 'EXAMPLES'),
        SEE_ALSO = colorise(MAN_SECTION_COLOR, 'SEE ALSO'),
        COPYRIGHT = colorise(MAN_SECTION_COLOR, 'COPYRIGHT'),
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
    def root_path():
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

    @staticmethod
    def _get_default_switch_file_path():
        return os.path.join(Env_switch.root_path(), 'default_switch')

    @staticmethod
    def get_default():
        default_switch = Env_switch._get_default_switch_file_path()
        if not os.path.isfile(default_switch):
            return None
        with open(default_switch, 'r') as ifstream:
            return ifstream.read().strip()

    @staticmethod
    def set_default(switch_name):
        with open(Env_switch._get_default_switch_file_path(), 'w') as ofstream:
            ofstream.write(switch_name)

    @staticmethod
    def is_default(switch_name):
        return (switch_name == Env_switch.get_default())

def item_or(seq, n, default = None):
    return (seq[n] if n < len(seq) else default)

def colorise(color, s):
    if (colored is None) or (color is None):
        return s
    return '{}{}{}'.format(
        colored.fg(color),
        s,
        colored.attr('reset'),
    )

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

    if tool == 'cc':
        os.execvp('viuact-cc', args)
    elif tool == 'link':
        os.execvp('viuact-opt', args)
    elif tool == 'fmt':
        os.execvp('viuact-format', args)
    elif tool == 'exec':
        pass
    elif tool == 'switch':
        if '--help' in args:
            print_help(
                executable = 'viuact-switch',
                text = HELP_SWITCH,
            )
            exit(0)

        switch_tool = item_or(args, 1, 'show')

        switch_root_exists = os.path.isdir(Env_switch.root_path())
        if (switch_tool != 'init') and not switch_root_exists:
            sys.stderr.write("error: run 'switch init' first\n")
            exit(1)

        if switch_tool == 'create':
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
                'lib/viua/std',
                'lib/viuact/Std',
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
        elif switch_tool == 'if':
            violent_exit = (item_or(args, 2) == '-e')
            switch_name = (
                item_or(args, 3)
                if violent_exit
                else item_or(args, 2))

            if switch_name is None:
                sys.stderr.write('error: no switch name\n')
                exit(1)
            if not Env_switch.exists(switch_name):
                sys.stderr.write(
                    'error: switch does not exist: {}\n'.format(switch_name))
                exit(1)

            is_active = Env_switch.is_active(switch_name)
            if (not is_active) and violent_exit:
                exit(1)

            if not violent_exit:
                print('true' if is_active else 'false')
            exit(0)
        elif switch_tool == 'init':
            if switch_root_exists:
                sys.stderr.write('warning: switch root already exists\n')
                # exit(0)

            root_path = Env_switch.root_path()
            init_path = os.path.join(root_path, 'init')

            share_path = os.path.expanduser('~/.local/share/viuact/switch/init')

            os.makedirs(root_path, exist_ok = True)
            os.makedirs(init_path, exist_ok = True)

            init_complete_zsh = os.path.join(init_path, 'complete.zsh')
            if os.path.isfile(init_complete_zsh):
                os.unlink(init_complete_zsh)
            os.link(
                src = os.path.join(share_path, 'complete.zsh'),
                dst = os.path.join(init_path, 'complete.zsh'),
            )
            with open(os.path.join(init_path, 'init.zsh'), 'w') as ofstream:
                with open(os.path.join(share_path, 'init.zsh'), 'r') as t:
                    ofstream.write(t.read().format(i = init_path))
        elif switch_tool == 'ls':
            enable_markers = ('-s' not in args)
            try:
                for switch_name in sorted(Env_switch.available_switches()):
                    is_active = Env_switch.is_active(switch_name)
                    is_default = Env_switch.is_default(switch_name)

                    color = (
                        None    if (not enable_markers) else
                        'green' if is_active else
                        'red'   if is_default else
                        None
                    )

                    fmt = ('{active}{default} {name}' if enable_markers else '{name}')
                    print(fmt.format(
                        active = (
                            '*'
                            if is_active else
                            ' '
                        ),
                        default = (
                            '='
                            if is_default else
                            ' '
                        ),
                        name = colorise(color, switch_name),
                    ))
            except FileNotFoundError:
                sys.stderr.write('error: switch directory does not exist\n')
                exit(1)
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
        elif switch_tool == 'show':
            show_default = ('--default' in args)
            switch_name = (
                Env_switch.get_default()
                if show_default else
                Env_switch.get_active()
            )
            if switch_name is None:
                sys.stderr.write('error: no {} switch\n'.format(
                    ('default' if show_default else 'active'),
                ))
                exit(1)
            if '--verbose' in args:
                print('switch: {}'.format(switch_name))
                print('prefix: {}'.format(os.path.join(Env_switch.switches_path(),
                    switch_name)))
            else:
                print(switch_name)
        elif switch_tool == 'to':
            switch_name = item_or(args, 2)
            set_default = False
            if switch_name == '--set':
                set_default = True
                switch_name = item_or(args, 3)
            if switch_name == '--default':
                switch_name = Env_switch.get_default()

            if switch_name is None:
                sys.stderr.write('error: no switch name to switch to\n')
                exit(1)
            if not Env_switch.exists(switch_name):
                sys.stderr.write(
                    'error: switch does not exist: {}\n'.format(switch_name))
                exit(1)

            switch_path = Env_switch.path_of(switch_name)
            def formatted_env_or_empty(variable):
                value = os.environ.get(variable)
                if value is None:
                    return ''
                if value[0] == ':':
                    return value
                return ':{}'.format(value)
            # export_line_fmt = '{key}={value}; export {key};\n'
            export_line_fmt = 'export {key}={value}\n'
            print(''.join(map(lambda x: export_line_fmt.format(
                key = x[0],
                value = x[1],
            ), {
                'VIUACT_SWITCH': switch_name,
                'VIUACT_SWITCH_PREFIX': switch_path,
                'VIUA_LIBRARY_PATH': '{sw}/lib/viua:{sw}/lib/viuact{env}'.format(
                    sw = switch_path,
                    env = formatted_env_or_empty('VIUA_LIBRARY_PATH')
                ),
                'VIUACT_LIBRARY_PATH': '{sw}/lib/viuact{env}'.format(
                    sw = switch_path,
                    env = formatted_env_or_empty('VIUACT_LIBRARY_PATH'),
                ),
                'PATH': '{sw}/bin{env}'.format(
                    sw = switch_path,
                    env = formatted_env_or_empty('PATH'),
                ),
                'MANPATH': '{sw}/man{env}'.format(
                    sw = switch_path,
                    env = formatted_env_or_empty('MANPATH'),
                ),
            }.items())), end = '')

            if set_default:
                Env_switch.set_default(switch_name)
        else:
            sys.stderr.write(
                'error: unknown switch subcommand: {}\n'.format(switch_tool))
            exit(1)

main(sys.argv[0], sys.argv[1:])
