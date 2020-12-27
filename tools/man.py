#!/usr/bin/env python3

import datetime
import os
import re
import shutil
import sys

import viuact.util.help


HELP = '''{NAME}
    {executable} - Read Viuact man pages

{SYNOPSIS}
    {exec_tool} [%arg(section)] [%arg(page)]

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

    %fg(man_se)intro%r
        Quick introduction to Viuact programming language.

{OPTIONS}
    %fg(man_se)--help%r
        Display this message.

{SEE_ALSO}
    viuact-cc(1)
    viuact-opt(1)
    viuact-format(1)

{COPYRIGHT}
    %copyright(2020) Marek Marecki

    %text
    This is Free Software published under GNU GPL v3 license.
'''


EXECUTABLE = 'viuact-man'


INTRO = '''%fg(man_se)VIUACT INTRODUCTION%r

    %text
    This is the short introduction to Viuact. Read this manual if you need to
    refresh your memory, or to get a quick glance of available language
    features. The introduction also discusses how to build (ie, compile and
    link) and run programs written in Viuact.

%fg(man_se)LANGUAGE FEATURES%r

    %text
    Viuact is a programming language with semantics inspired by C++, Erlang, and
    OCaml. The actor model is used for the underlying philosophy of the
    language, with each actor being a sequentially-executed process in which
    every expression is eagerly evaluated.

  %fg(man_se)CODE ORGANISATION%r

    %text
    Code is organised in functions (no executable text may be present outside of
    a function definition), and execution begins from the function named main:

        %fg(white)(val main () -> i64)
        (let main () {{
            (print "Hello, World!")
            0
        }})%r

    %text
    The main function must return a value of i64 type (ie, a signed 64-bit wide
    integer). Function definitions (let foo) must be preceded by signatures (val
    foo).

    %text
    A function's body is a single, but arbitrarily complex, expression. Several
    expressions may be "grouped" together and be treated as a single expression
    by wrapping them in braces (ie, the {{ and }} characters) as in the example
    above.

  %fg(man_se)DATA TYPES%r

    %text
    The language allows defining new data types. These may be simple records
    akin to C structs:

        %fg(white)(type record_name {{
            (val field_name i8)
        }})%r

    ...or strong enumerations (ie, sum types):

        %fg(white)(enum option (
            (Some 'a)
            None
        ))%r

  %fg(man_se)CONTROL FLOW%r

    %text
    In terms of flow control the language offers three main tools: a basic
    conditional expression (if), a match expression (match-with), and a function
    call (tail calls are fully supported).

    %fg(man_se)IF EXPRESSION%r

    %text
    The conditional expression is simple. It takes an arbitrary guard
    expression (displayed in %fg(yellow)yellow%r), evaluates it, and if the
    value is true executes the "truth" expression (displayed in
    %fg(green)green%r), otherwise it executes the "false" expression (displayed
    in %fg(red)red%r).

        %fg(white)(if %fg(yellow)something%r
            %fg(green)"If true."
            %fg(red)"If false."%fg(white))%r

    %text
    If the conditional expression is needed just to guard another expression
    (ie, it should only execute something if the guard is true) the "drop token"
    (ie, the _ character) can be used in place of the "false" expression, see
    example below:

        %fg(white)(if something {{
            (print "engaging procedure")
            (some_procedure)
        }} _)%r

    %text
    In such case, the value of the conditional expression must not be used since
    it is not guaranteed to be there as the drop token does not produce anything!

    %fg(man_se)MATCH EXPRESSION%r

    %text
    The match expression's guard expression must evaluate to a value of an
    enumeration type. Each clause of the match then deals with a distinct
    enumeration case:

        %fg(white)(match something (
            (with Some a (print a))
            (with None   (print "nothing"))
        ))%r

    %text
    The compiler rejects the source code if the match expression does not have a
    clause for every case of the enumeration type being matched. The drop token
    may be used to create a catch-all clause.

    %fg(man_se)FUNCTION CALL%r

    %text
    To call a function simply state its name, followed by a suitable sequence of
    arguments:

        %fg(white)(print "Hello, World!")
        (answer_the_question 42)%r

    %fg(man_se)TAIL CALL%r

    %text
    Tail calls are enabled on programmer's request. To turn an ordinary call
    into a tail call add the "tailcall" keyword before the function's name:

        %fg(white)(tailcall answer_the_question 42)%r

    %text
    Value produced by such a call cannot be used as the call frame is "hijacked"
    by the callee (ie, answer_the_question in the example) and the caller is no
    more. The value produced by such a call will be visible only in the
    grand-caller as-if it was the return value produced by the original caller.

    %fg(man_se)ACTOR CALL%r

    %text
    The ability to call functions concurrently is provided by actors. Similarly
    to tail calls, calling function as an actor requires a keyword:

        %fg(white)(actor run_server 8080)%r

    %text
    Such a call does not produce a value directly. Instead, a PID is returned
    which can be used to wait for the actor to complete and obtain its return
    value. PID can also be used to send a message to the actor (to send it
    additional data, to request a progress report, etc).

  %fg(man_se)ERROR HANDLING%r

    %text
    Errors are signalled using exceptions. An exception can be "thrown" using a
    throw expression:

        %fg(white)(throw Errno 42)%r

    %text
    A try expression may be used to guard against exceptions:

        %fg(white)(try {{
            ...
        }} (
            (catch Errno a {{
                (report_errno a)
                (produce_default_value)
            }})))%r

    %text
    An exception type must be declared before it can be used. It may carry a
    field of specified type:

        %fg(white)(exception Error)
        (exception Errno i64)%r

  %fg(man_se)I/O%r

    %text
    All I/O is asynchronous and performed using I/O ports and requests.

    FIXME examples of I/O

%fg(man_se)BUILDING AND RUNNING%r

    %text
    Building a program written in Viuact is a two-step process. First you have
    to compile the Viuact source code into an equivalent program written in Viua
    VM assembly language. Then you have to assemble and link the final
    executable.

    %text
    The first step is performed by the %fg(white)viuact-cc(1)%r program:

        %fg(white)viuact cc example.vt%r

    %text
    This will produce an example.asm file in the build/_default directory. The
    next step is to convert the assembly source code into a bytecode module,
    link it, and produce the final executable:

        %fg(white)viuact opt build/_default/example.asm%r

    %text
    If successful, the above command will save its output in example.bc file in
    the build/_default directory. The file contains executable Viua VM bytecode
    which can be run using the %fg(white)viua-vm(1)%r interpreter:

        %fg(white)viua-vm build/_default/example.bc%r

{COPYRIGHT}
    %copyright(2020) Marek Marecki

    %text
    This is Free Software published under GNU GPL v3 license.
'''


PAGES = {
    'intro': INTRO,
}


def item_or(seq, n, default = None):
    return (seq[n] if n < len(seq) else default)

def main(executable_name, args):
    arg = (args[0] if args else '--help')

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
        exit(0)

    if arg == '--help':
        viuact.util.help.print_help(
            EXECUTABLE,
            suite = viuact.suite,
            version = viuact.__version__,
            text = HELP,
        )
        exit(0)

    page = arg
    viuact.util.help.print_help(
        EXECUTABLE,
        suite = viuact.suite,
        version = viuact.__version__,
        text = PAGES[page],
    )
    exit(0)

main(sys.argv[0], sys.argv[1:])
