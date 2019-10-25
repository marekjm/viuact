# Viuact

High-level programming language for [Viua](https://viuavm.org) virtual machine.

Viuact has a Lisp-inspired syntax and strong, dynamic typing. Some features of
the language include:

- nested functions and closures
- tail calls
- actor-based concurrency (inherited from Viua VM)
- message passing as means of communication between actors 
- module system

----

## Hello, World!

This is how you write the canonical program:

    (let main () (print "Hello, World!"))

Save this code to a file (`vim`), compile (`viuact-cc`), assemble and
link (`viuact-opt`), and execute (`viua-vm`):

    $ vim hello.lisp
    $ viuact-cc --mode exec hello.lisp
    $ viuatc-opt build/_default/hello.asm
    $ viua-vm build/_default/hello.bc
    Hello, World!
    $

----

## Brief introduction

Let-bindings are used to define functions and variables:

    (let main () {
        (let x "Hello, World!")
        (print x)
        0
    })

Functions and variables are pretty much the same: let-bindings bind values to
names. Functions are just parametrised expressions whose evaluation is delayed
until they are called, but they too ultimately produce a value.

Let-bindings always bind a name to a single expression. An expression can be a
simple one (e.g. `42` or `(print "Hello, World!")`) or a compound one. Compound
expressions are enclosed in braces (`{ ... }`) which may contain one or more
expressions (which can be simple or compound, there is no restriction on nesting
them).

Functions are called by enclosing their name and arguments in parentheses, like
this: `(print x)`.

The "return value" of the compound expression is the value of the last
expression in the body of the compound expression. It is 0 in the example above.

Conditional expressions are used to make decisions:

    (let main () {
        (let x (get_answer_to "What is the meaning of life?"))
        (let correct_answer 42)
        (let exit_code (if (= x correct_answer)
            {
                (print "Wow, how did you know?")
                0
            }
            {
                (print "Nope, that's not it.")
                1
            }))
        exit_code
    })

Results of conditional expressions are values so "ifs" can be used everywhere an
expression can be used, e.g. in let-bindings.

----

## Full introduction

A not-so-brief introduction to teh language is available in docs directory, see
[the specification](./docs/SPEC.markdown).

----

# License

Viuact compiler is Free Software.
It is published under GNU GPL v3.
