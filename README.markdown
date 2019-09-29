# Viuact

```
(let main () (print "Hello, World!"))
```

This repository contains source code of a compiler from a high level language
with Lisp-like syntax to Viua VM assembly.

Some of the language features include:

- nested functions
- externally immutable closures
- module system
- let-bindings as means of remembering values
- tail calls
- actor calls (spawning parallel processes)
- message passing as means of communications between actors

----

# Usage example

This example will compile the `./sample/example.lisp` file.
The file is neither particularly instructive, nor a paragon of good code
design, but it serves as a "kitchen sink" file and contains code that
uses almost all functionality the compiler supports, so is a good stress
test.

Anyway. We talked the talk, now we should walk the walk:

```
$ ./cc.py --mode exec sample/example.lisp
$ ./opt.py build/_default/example.asm
$ viua-vm a.out
```

There are three commands needed to run the code.
Only the first two are part of the compiler.
For step-by-step explanation, read on.

## Compilation

```
$ ./cc.py --mode exec sample/example.lisp
```

This command will analyse the input file (`sample/example.lisp`) and
emit:

- `.asm` files that contain compiled code
- `.i` files that contain module interfaces (i.e. exported functions)
- `.d` files that contain dependency information (only for executables;
  but this will change to allow imports in modules)

This command will not perform assembly or linkage.

## Assembly and linkage

```
$ ./opt.py build/_default/example.asm
```

This command will assemble the input file, turning it into an executable
binary.
It will also read dependency information from the `.d` file associated
with the input file. Dependency information is needed to compile modules
imported by the input file and link them to the main executable.

## Executing

```
$ viua-vm a.out
```

This will execute the compiled file.

## Abstracted away

```
$ ./cc.py --mode exec {dir}/{name}.lisp
$ ./opt.py build/_default/{name}.asm
$ viua-vm a.out
```

----

# License

The code is licensed under GNU GPL v3.
