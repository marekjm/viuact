#!/usr/bin/env python3

import datetime
import os
import re
import shutil
import sys

import viuact
import viuact.frontend
import viuact.driver
import viuact.env
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

HELP_SWITCH = '''{NAME}
    {executable} - Manage multiple language versions

{SYNOPSIS}
    {exec_tool} <%fg(man_const)tool%r> [%arg(option)...] [%arg(arg)]
    {exec_blank} --help
    {exec_blank} create [%arg(option)] %arg(name)
    {exec_blank} if     [%arg(option)] $arg(name)
    {exec_blank} init
    {exec_blank} ls     [%arg(option)]
    {exec_blank} rm     %arg(name)
    {exec_blank} show   [%arg(option)]
    {exec_blank} to     [%arg(option)...] [%arg(name)]

{DESCRIPTION}
    %text
    This executable is a front for tooling supplied for the Viuact langauge. It
    can be used as a driver for those other tools (compiler, linker, formatter).
    Each tool can be used on its own without this wrapper.

    %text
    This is also an executable that can be used to inspect state of the Viuact
    installation on a system by checking paths, environment variables' values,
    etc.

{COMMANDS}
    %text
    If no command is given, the default is %fg(man_se)show%r.

    %fg(man_se)create%r %arg(name)
        Create new switch named %arg(name).

    %fg(man_se)if%r %arg(name)
        %text
        Check if %arg(name) is the active switch. Prints
        %fg(bool)true%r to standard output if swith %arg(name) is
        active; %fg(bool)false%r otherwise. Always exit with 0 unless
        %opt(-e) option is present on the command line.

        %opt(-e)
            %text
            Instead of printing to standard output use exit code to signal the
            result of the operation. Exit with %fg(int)0%r if switch
            %arg(name) is active; %fg(int)1%r otherwise.

    %fg(man_se)init%r
        %text
        Initialise switch root directory. This command needs to be executed
        before any other %fg(man_se)viuact switch%r command.

    %fg(man_se)ls%r
        %text
        List created switches. Active switch is prepended with * and its name is
        displayed %fg(green)green%r. Default switch is prepended with = and its
        name is displayed %fg(red)red%r.

        %opt(-s)
            Do not prepend markers to switch names and disable coloring.

    %fg(man_se)rm%r %arg(name)
        Remove switch named %arg(name).

    %fg(man_se)show%r
        %text
        Show active switch. If the %opt(--default) option is given then
        show the default switch. The %opt(--verbose) option may be used
        to get information about the active switch.

        %opt(--verbose)
            %text
            Show information about the active switch instead of just its name.

        %opt(--default)
            Use default switch instead of the active one.

    %fg(man_se)to%r %arg(name)
        %text
        Emit shell script required to activate a switch named %arg(name).
        Use `%fg(man_se)viuact switch to %fg(man_var)foo%r` to activate a switch
        named %fg(man_var)foo%r. Use %opt(--set) option to also set the
        switch as default.

        %opt(--set)
            %text
            Set the switch %arg(name) as default in addition to emitting
            the activating commands.

        %opt(--default)
            Activate the default switch.

{OPTIONS}
    %fg(man_se)--help%r
        Display this message.

{SEE_ALSO}
    viuact-cc(1)
    viuact-opt(1)
    viuact-format(1)

{COPYRIGHT}
    %copyright(2020) Marek Marecki

    This is Free Software published under GNU GPL v3 license.
'''


EXECUTABLE = 'viuact'


CORE_TOOLS = (
    'cc',
    'opt',
    'fmt',
)
KNOWN_TOOLS = (
    *CORE_TOOLS,
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

DEFAULT_CORE_DIR = '.'
CORE_DIR = os.environ.get('VIUACT_CORE_DIR', DEFAULT_CORE_DIR)
def get_core_exec_path(executable):
    is_development = (CORE_DIR == '.')
    return os.path.join(os.path.expanduser(CORE_DIR), {
        'cc': ('cc.py' if is_development else 'viuact-cc'),
        'fmt': ('format.py' if is_development else 'viuact-format'),
        'opt': ('opt.py' if is_development else 'viuact-opt'),
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
    elif tool == 'switch':
        if '--help' in args:
            viuact.util.help.print_help(
                executable = 'viuact-switch',
                suite = viuact.suite,
                version = viuact.__version__,
                text = HELP_SWITCH,
            )
            exit(0)

        switch_tool = item_or(args, 1, 'show')

        switch_root_exists = os.path.isdir(Env_switch.root_path())
        if (switch_tool != 'init') and not switch_root_exists:
            sys.stderr.write("error: run 'switch init' first\n")
            exit(1)

        SWITCH_EXECUTABLES = (
            'viua-vm',
            'viua-asm',
            'viua-dis',
        )
        SWITCH_CORE_EXECUTABLES = (
            'viuact-cc',
            'viuact-opt',
            'viuact-format',
        )

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

            BUILD_DIR = 'var/viuact/build'
            CONFIG_DIR = 'etc/viuact'

            SWITCH_DIRS = (
                'bin',              # Executables
                'etc',              # Configuration
                'init',             # Viuact init files
                'lib',              # Libraries
                'lib/viuact-core',  # Core Viuact executables
                'lib/viuact/Std',   # Standard Viuact libraries
                'lib/viua/std',     # Standard Viua VM libraries
                'man',              # man(1) pages
                'run',              # Runtime state (PID and socket files, etc.)
                'share',            # Resource files
                'var',              # Variable and accumulated state
                'var/cache',        # Cache
                'var/log',          # Logs

                BUILD_DIR,          # Build files produced during switch
                                    # creation and package installation
                CONFIG_DIR,         # Configuration for this switch
            )
            for each in SWITCH_DIRS:
                os.makedirs(os.path.join(switch_path, each))

            BASE_BIN_DIR = os.path.expanduser('~/.local/bin')
            BASE_CORE_DIR = os.path.expanduser('~/.local/lib/viuact-core')

            SWITCH_BIN_DIR = os.path.join(switch_path, 'bin')
            SWITCH_CORE_DIR = os.path.join(switch_path, 'lib/viuact-core')

            for each in SWITCH_CORE_EXECUTABLES:
                shutil.copyfile(
                    src = os.path.join(BASE_CORE_DIR, each),
                    dst = os.path.join(SWITCH_CORE_DIR, each),
                )

            BASE_TEMPLATE_INIT_DIR = os.path.expanduser(
                '~/.local/viuact/switch/init/here')
            SWITCH_INIT_DIR = os.path.join(switch_path, 'lib/viuact-core')
            INIT_FILES = (
                'commonrc',
                '.zshrc',
            )

            SWITCH_BUILD_DIR = os.path.join(switch_path, BUILD_DIR)
            os.chdir(SWITCH_BUILD_DIR)
            if True:  # Build and install Viua VM
                stage_dir = os.path.join(SWITCH_BUILD_DIR, 'viuavm')
                os.makedirs(stage_dir)
                os.chdir(stage_dir)

                GIT_REPOSITORY = 'https://git.sr.ht/~maelkum/viuavm'
                GIT_BRANCH = 'devel'
                GIT_COMMIT = None
                def run_git_clone(repository, branch = None, commit = None):
                    cmd = 'git clone '
                    if branch is not None:
                        cmd += '--branch {}'.format(branch)

                    if os.system('{} {} .'.format(cmd, repository)) != 0:
                        fmt = 'error: command failed: {}\n'.format(cmd)
                        sys.stderr.write(fmt.format(cmd))
                        exit(1)

                    if commit is None:
                        return

                    cmd = 'git checkout {}'.format(commit)
                    if os.system(cmd) != 0:
                        fmt = 'error: command failed: {}\n'.format(cmd)
                        sys.stderr.write(fmt.write(cmd))
                        exit(1)

                run_git_clone(GIT_REPOSITORY, GIT_BRANCH, GIT_COMMIT)
                if os.system('./scripts/compile') != 0:
                    fmt = 'error: compilation of Viua VM failed\n'
                    sys.stderr.write(fmt)
                    exit(1)

                install_cmd = 'make PREFIX={} install'.format(switch_path)
                if os.system(install_cmd) != 0:
                    fmt = 'error: installation of Viua VM failed\n'
                    sys.stderr.write(fmt)
                    exit(1)

            SWITCH_CONFIG_DIR = os.path.join(switch_path, CONFIG_DIR)
            with open(os.path.join(SWITCH_CONFIG_DIR, 'created.conf'), 'w') as ofstream:
                ofstream.write('[creation]\n')
                ofstream.write('\n'.join(map(lambda x: '    {} = {}'.format(*x), {
                    'date_created':
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'switch_root': switch_root,
                    'switch_name': switch_name,
                    'viuact_version': '{} ({})'.format(
                        viuact.__version__,
                        viuact.__commit__,
                    ),
                }.items())))
                ofstream.write('\n')
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
                        name = viuact.util.help.colorise(color, switch_name),
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
                'VIUACT_CORE_DIR': '{sw}/lib/viuact-core'.format(
                    sw = switch_path,
                ),
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
                'MANPATH': '{env}:{sw}/man'.format(
                    sw = switch_path,
                    env = formatted_env_or_empty('MANPATH'),
                ),
            }.items())), end = '')

            if set_default:
                Env_switch.set_default(switch_name)
        elif switch_tool == 'update':
            verbose_report = ('--verbose' in args)
            dry_run = ('--dry-run' in args)
            force = ('--force' in args)

            switch_name = item_or(args, (len(args) - 1))
            if switch_name.startswith('--'):
                switch_name = None

            if switch_name is None:
                sys.stderr.write('error: no switch name\n')
                exit(1)
            if not Env_switch.exists(switch_name):
                sys.stderr.write(
                    'error: switch does not exist: {}\n'.format(switch_name))
                exit(1)

            switch_path = Env_switch.path_of(switch_name)

            BASE_BIN_DIR = os.path.expanduser('~/.local/bin')
            BASE_CORE_DIR = os.path.expanduser('~/.local/lib/viuact-core')

            SWITCH_BIN_DIR = os.path.join(switch_path, 'bin')
            SWITCH_CORE_DIR = os.path.join(switch_path, 'lib/viuact-core')

            def read_vm_version(prefix):
                vm_version = os.popen('{}/viua-vm --version --verbose'.format(
                    prefix), 'r').read()
                try:
                    basic, fingerprint = vm_version.splitlines()
                except Exception:
                    fmt = 'error: cannot read version from: {}/viua-vm\n'
                    sys.stderr.write(fmt.format(prefix))
                    fmt = 'note: returned string:\n{}\n'
                    sys.stderr.write(fmt.format(vm_version))
                    exit(1)

                basic = basic.rsplit(maxsplit = 2)
                basic = (basic[1], basic[2].replace('(', '').replace(')', ''),)
                fingerprint = fingerprint.rsplit(maxsplit = 1)[1]

                return (basic, fingerprint,)
            def format_vm_version(vm_version, fingerprint_chars = None):
                basic, fingerprint = vm_version
                version, commit = basic

                fingerprint_chars = (fingerprint_chars or 8)
                return '{} {} {}...{}'.format(
                    version,
                    commit,
                    fingerprint[:fingerprint_chars],
                    fingerprint[-fingerprint_chars:],
                )

            old_vm_version = read_vm_version(SWITCH_BIN_DIR)
            new_vm_version = read_vm_version(BASE_BIN_DIR)

            if (old_vm_version == new_vm_version) and not force:
                sys.stderr.write('error: update not needed\n')
                sys.stderr.write('note: switch VM: {}\n'.format(
                    format_vm_version(old_vm_version, fingerprint_chars = 16),
                ))
                exit(0)

            if verbose_report:
                print('from-version:     {}'.format(old_vm_version[0][0]))
                print('from-commit:      {}'.format(old_vm_version[0][1]))
                print('from-fingerprint: {}'.format(old_vm_version[1]))
                print('to-version:       {}'.format(new_vm_version[0][0]))
                print('to-commit:        {}'.format(new_vm_version[0][1]))
                print('to-fingerprint:   {}'.format(new_vm_version[1]))
            else:
                print('from: {}'.format(format_vm_version(old_vm_version)))
                print('to:   {}'.format(format_vm_version(new_vm_version)))

            if dry_run:
                exit(0)

            for each in SWITCH_EXECUTABLES:
                os.unlink(
                    os.path.join(SWITCH_BIN_DIR, each),
                )
                shutil.copy(
                    src = os.path.join(BASE_BIN_DIR, each),
                    dst = os.path.join(SWITCH_BIN_DIR, each),
                )
        else:
            sys.stderr.write(
                'error: unknown switch subcommand: {}\n'.format(switch_tool))
            exit(1)
    else:
        sys.stderr.write('warning: tool not implemented\n')
        exit(1)

    exit(0)

main(sys.argv[0], sys.argv[1:])
