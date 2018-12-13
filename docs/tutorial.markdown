# Viuact tutorial

This tutorial will teach you how to write simple programs in Viuact.
It expects you to have some previous programming experience, and to be
comfortable using \*NIX command line environment.

It is assumed that you start every chapter inside Viuact compiler's repository.

--------------------------------------------------------------------------------

# Hello World!

Enter this text into a file named `hello.lisp`:

```
(let main () (
    (print "Hello World!")
))
```

The syntax looks Lispy, but the semantics are not. Do not let that fool you; the
file extension is chosen to reuse the syntax highlighting rules of common text
editors.

Then, execute the following commands to compile your program:

```
$ ./src/viuact-cc.py --mode exec hello.lisp
$ ./src/viuact-opt.py build/_default/hello.asm
```

They should leave you with a file `a.out` (after *a*ssembler's *out*put).
This is a binary file executable by the Viua VM kernel. You can run it like
this:

```
$ viuavm-kernel a.out
Hello World!
$
```

If you saw "Hello World!" printed to your screen - congratulations! You have
just written your first Viuact program. We will now go through the process in
a step-by-step fashion, and I will explain every step to you along the way.

----

## Defining a function

A function definition is introduced by the `let` keyword. It looks like this:

```
(let <function-name> ( <parameters>... ) ( <expr> <expr>... ))
```

Some valid function definitions include:

```
; Print whatever is passed to the function.
(let f (x) (
    (print x)
))

; Add one to the integer that is passed to the function.
(let add_1 (n) (
    (+ n 1)
))
```

The whole function definition is wrapped by parentheses, the list of parameters
is wrapped in parentheses, and the list of expressions that makes up the
function's body is also wrapped in parentheses.

----

## Creating variables

Variables are introduced by the `let` keyword. A variable binding looks like
this:

```
(let <name> <expr>)
```

Some valid variable bindings:

```
(let answer 42)
(let x (f answer))
```

Names can be rebound to new values.
