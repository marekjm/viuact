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

We will now go through the process of creating a slightly more complex program,
in a step-by-step fashion, and I will explain every step to you along the way.

--------------------------------------------------------------------------------

# A more complex example
