#compdef viuact

#
# Based on complete.zsh file from OCaml's Opam.
#

if [ -z "$ZSH_VERSION" ]; then return 0; fi

# Adds completions directly.
_viuact_add()
{
    IFS=$'\n' _viuact_reply+=("$@")
}

# Adds completions from an executed command.
_viuact_add_f()
{
    local cmd
    cmd=$1; shift
    _viuact_add "$($cmd "$@" 2>/dev/null)"
}

_viuact_flags()
{
    echo "--env"
    echo "--help"
    echo "--verbose"
    echo "--version"
}

_viuact_commands()
{
    echo "cc"
    echo "fmt"
    echo "link"
    echo "switch"
}

_viuact_vars()
{
    # see: opam config list --safe
}

_viuact_argtype()
{
    local cmd flag
    cmd="$1"; shift
    flag="$1"; 

    case "$cmd" in
        cc)
            case "$flag" in
                --mode)
                    echo CC_MODE
                    return 0
                    ;;
                *) ;;
             esac;;
        *) ;;
    esac
    case "$flag" in
        --help)
            echo BREAK
            return 0
            ;;
        --version)
            echo VERBOSE_ONLY
            return 0
            ;;
        -*) ;;
    esac

    echo NONE
}

_viuact()
{
    local IFS cmd subcmd cur prev compgen_opt

    COMPREPLY=()
    cmd=${COMP_WORDS[1]}
    subcmd=${COMP_WORDS[2]}
    cur=${COMP_WORDS[COMP_CWORD]}
    prev=${COMP_WORDS[COMP_CWORD-1]}
    compgen_opt=()
    _viuact_reply=()

    if [ $COMP_CWORD -eq 1 ]; then
        _viuact_add_f _viuact_commands
        _viuact_add_f _viuact_flags
        COMPREPLY=( $(compgen -W "${_viuact_reply[*]}" -- $cur) )
        unset _viuact_reply
        return 0
    fi

    echo "COMP_CWORD := $COMP_CWORD" >> debug.txt
    echo "COMP_CWORDS := $COMP_CWORDS" >> debug.txt
    echo "cmd := $cmd" >> debug.txt
    echo "subcmd := $subcmd" >> debug.txt
    echo "cur := $cur" >> debug.txt
    echo "prev := $prev" >> debug.txt

    case "$(_viuact_argtype $cmd $prev)" in
        FILE|FILENAME) compgen_opt+=(-o filenames -f);;
        VIUACT_SOURCE_FILE)
            _viuact_add_f find . -name '*.vt'
            _viuact_add_f find . -name '*.viuact'
            ;;
        DIR|ROOT) compgen_opt+=(-o filenames -d);;
        MAKE|CMD) compgen_opt+=(-c);;
        KIND) _viuact_add http local git;;
        WHEN) _viuact_add always never auto;;
        SWITCH|SWITCHES) _viuact_add_f viuact switch ls -s;;
        SHELL) _viuact_add bash sh zsh;;
        CC_MODE)
            _viuact_add module exec auto
            ;;
        TAGS) ;;
        BREAK) ;;
        VERBOSE_ONLY)
            _viuact_add --verbose
            ;;
        NONE|)
    case "$cmd" in
        cc)
            case $COMP_CWORD in
                2)
                    _viuact_add --help --version --mode --env
                    ;;
                4)
                    _viuact_add_f find . -name '*.vt'
                    _viuact_add_f find . -name '*.viuact'
                    ;;
                *)
                    _viuact_add --help --version --mode --env
                    ;;
            esac
            ;;
        link)
            _viuact_add_f find ./build/_default -name '*.asm'
            _viuact_add --help --version
            ;;
        fmt)
            _viuact_add_f find . -name '*.vt'
            _viuact_add_f find . -name '*.viuact'
            _viuact_add --help --version -i -s
            ;;
        switch)
            case $COMP_CWORD in
                2)
                    _viuact_add create if init ls rm show to
                    _viuact_add --help
                    ;;
                *)
                    case "$subcmd" in
                        create)
                            if [ $COMP_CWORD -eq 3 ]; then
                                _viuact_add --set
                            fi
                            ;;
                        if)
                            if [ $COMP_CWORD -eq 3 ]; then
                                _viuact_add -e
                                _viuact_add_f viuact switch ls -s
                            elif [ "$prev" == '-e' ]; then
                                # FIXME for some reason _viuact_add_f does not
                                # work here
                                _viuact_add "$(viuact switch ls -s)"
                            fi
                            ;;
                        init) ;;
                        ls)
                            _viuact_add -s
                            ;;
                        rm)
                            _viuact_add_f viuact switch ls -s
                            ;;
                        show)
                            if [ $COMP_CWORD -eq 3 ]; then
                                _viuact_add --verbose --default
                            elif [ $COMP_CWORD -eq 5 ]; then
                                true
                            elif [ "$prev" == '--default' ]; then
                                _viuact_add --verbose
                            elif [ "$prev" == '--verbose' ]; then
                                _viuact_add --default
                            fi
                            ;;
                        to)
                            if [ $COMP_CWORD -eq 3 ]; then
                                _viuact_add --set --default
                                _viuact_add_f viuact switch ls -s
                            elif [ "$prev" == '--set' ]; then
                                # FIXME for some reason _viuact_add_f does not
                                # work here
                                _viuact_add "$(viuact switch ls -s)"
                            fi
                            ;;
                        *) ;;
                    esac;;
            esac;;
        *) ;;
    esac;;
    esac

    COMPREPLY=($(compgen -W "${_viuact_reply[*]}" "${compgen_opt[@]}" -- "$cur"))
    unset _viuact_reply
    return 0
}

autoload bashcompinit
bashcompinit
complete -F _viuact viuact
