# Viuact compiler

A compiler from a high level language to Viua VM assembly.

```
(let main () (
    (print "Hello World!")
))
```

The language has Lisp-like syntax, described in full in
[SYNTAX](SYNTAX.txt) file. Some of its features include:

- nested functions
- externally immutable closures
- module system
- let-bindings as means of remembering values
- tail calls
- actor calls (spawning parallel processes)
- message passing (via direct send and receive between actors)

----

# Usage example

This example will compile the `./sample/example.lisp` file.
The file is neither particularly instructive, nor a paragon of good code
design, but it serves as a "kitchen sink" file and contains code that
uses almost all functionality the compiler supports, so is a good stress
test.

Anyway. We talked the talk, now we should walk the walk:

```
$ ./src/viuact-cc.py --mode exec sample/example.lisp
$ ./src/viuact-opt.py build/_default/example.asm
$ ../core/viuavm/build/bin/vm/kernel a.out
```

There are three commands needed to run the code.
Only the first two are part of the compiler.
For step-by-step explanation, read on.

## Compilation

```
$ ./src/viuact-cc.py --mode exec sample/example.lisp
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
$ ./src/viuact-opt.py build/_default/example.asm
```

This command will assemble the input file, turning it into an executable
binary.
It will also read dependency information from the `.d` file associated
with the input file. Dependency information is needed to compile modules
imported by the input file and link them to the main executable.

## Executing

```
$ ../core/viuavm/build/bin/vm/kernel a.out
```

This will execute the compiled file.

## Abstracted away

```
$ ./src/viuact-cc.py --mode exec {dir}/{name}.lisp
$ ./src/viuact-opt.py build/_default/{name}.asm
$ ../core/viuavm/build/bin/vm/kernel a.out
```
