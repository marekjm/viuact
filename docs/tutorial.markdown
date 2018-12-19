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
just written your first Viuact program.

We will now go through the process of creating slightly more complex programs,
in a step-by-step fashion, and I will explain every step to you along the way.

--------------------------------------------------------------------------------

# A more complex example: nested functions and closures

In this example you will learn how to write nested functions and closures. You
will also learn the caveats of working with closures in Viuact, and how they
differ from closures in other languages (Javascript and C++).

--------------------------------------------------------------------------------

# A more complex example: math functions

The more complex example will include building a program that computes Fibonacci
numbers and powers. We will start with an empty file, follow up with writing the
functions to the computation, and end with extracting the functions to an inline
module. Then, we will move the inline module to a separate file.

--------------------------------------------------------------------------------

# A more complex example: message passing

In this example we will build a message ring - a program that will spawn several
concurrent processes that will route a single message until it returns to the
original sender. This will allow us to learn how message passing works in
Viuact.
