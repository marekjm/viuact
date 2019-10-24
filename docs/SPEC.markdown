# Viuact language specification

This document presents Viua VM language specification.

- modules
  - inline modules
  - modules in separate files
  - imports
  - interface files
- enumerations (and custom field values)
- let-binding (variable)
  - allowed variable names (`a` and `a'`)
- let-binding (function definition)
  - allowed parameter names (`a`, `a'`, and `~a`)
  - positional and labeled parameters (with label punning)
  - nested functions
  - closures
  - return values
- *if* expression
- function call
- actor call
- tail call
- operator call
- struct field access
- literals (int, float, text, struct, vector)
- simple and compound expressions (and their return values)
- exception handling
- comments

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

### Return values

A function always returns the value of the last expression in its body.
Explicit returns are usually unnecessary in Viuact.

### Nested functions

Functions may be defined inside other functions, like this:

```
(let fn (x) (
    (let foo (z) (
        (print z)
    ))
    (foo z)
))
```

### Closures

Closures may be easily created the same way as nested functions:

```
(let fn (x) (
    (let foo () (
        (print x)
    ))
    (foo)
))
```

If a nested function uses a variable that is defined in the immediate lexical
scope it is defined in the function is automatically converted to a closure.

You have to note that closures do not *share* the variable they capture, but
*copy* it from their outer scope and hold on to an their own, independent copy.

> Note: The behaviour is defined this way because it is easier to implement.
> We have a very tight time budget for this project, so we need to cut some
> corners to be able to deliever something that works.

----

## Creating variables

Variables are introduced by the `let` keyword. A variable binding looks like
this:

```
(let <name> <expr>)
```

The `<expr>` part may be any expression that can be bound by a let-binding:

- a literal (e.g. `42`, `"Hello World!"`, or `-3.14`)
- a function call result (e.g. `(frobnicate 42)` or `(Std.Posix.Io.open "./foo.txt")`)
- an operator call result (e.g. `(+ x 1)`)
- a result of a compound expression (e.g. `{ ... }`)
- a result of an if expression (`if <expr> <true-arm> <false-arm>`)

A few examples of valid variable bindings are:

```
(let answer 42)
(let x (frobnicate answer))
(let y (+ x 1))
```

Names can be rebound to new values:

```
; config_file now represents a path to the config file.
(let config_file "~/.config/foo/foo.conf")

; Here, the previous value is consumed and the name is rebound to represent a
; file descriptor.
(let config_file (Std.Posix.Io.open config_file)

; Here, the name is rebound once more to represent a parsed configuration file.
(let config_file (Config.parse_fd config_file))
```

There is no assignment operator in Viuact. Whenever you want to modify a value,
you must rebind its name to a modified version of it.

----

## Conditional expressions

The only conditional expression available is a simple if.
The if expression has:

- a condition: always evaluated to determine which arm should be evaluated
- a true arm: evaluated only when the condition is true
- a false arm: evaluated only when the condition is false

The value of the if expression is the value of either true arm expression, or
false arm expression (depending on the value of the condition epression).

All expressions that make up the if expression may be arbitrarily complex.

----

## Modules

Viuact has a simple module system.
Modules can be defined only in the top-level file scope, or inside other modules.

### Module definitions

A module is a sequence of:

- module imports
- module definitions or declarations
- function definitions

No other forms may appear inside immedate module body.

### Inline modules

A module may be defined "inline" inside another module, or inside an executable.
It is written like this:

```
(module A_module (
    ; imports, module declarations or definitions, function definitions
))
```

After compilation an inline module is put in a separate file. There is no
difference between modules defined inline and out-of-line. This also means that
an inline module must be explicitly imported to use it.

> Note: The fact that inline must be explicitly imported is there to provide
> consistency - it should not matter whether the module is defined inline, or
> out-of-line.

### Module declarations

A module declaration specifies that the module that is just being compiled has
a nested module that should also be compiled.
Such a structure allows the compiler to automatically discover the structure of
modules in a project.

> Note: There is prior art to this approach - the Rust programming language
> follows the same model of inline and out-of-line modules.

A module declaration looks like this:

```
; contents defined in A_module.lisp
(module A_module)
```

The contents of declared module must be put inside the file that has the same
name as the module (e.g. `(module A_module)` requires `A_module.lisp` file to
exists), with the `.lisp` extension.

The source file of the nested module must exist inside a directory named after
the module containing the declaration. For example, assuming an `X_module.lisp`
file with the following content:

```
(module A_module)
```

we know that there is a module named `X_module` that has a nested module named
`A_module`. So the file and directory structure must look like this:

```
X_module.lisp
X_module/A_module.lisp
```

If the compiler is unable to find the required files it must abort the
compilation with an error.

### Module imports

Module imports begin with the `import` keyword. It is followed by a module name;
either qualified or not.

```
; Import of an unqualified name.
(import A_module)

; Import of a qualified name.
(import A_module.B_module.C_module)
```

Imports of qualified names are used to import nested modules.
Every module used must be imported explicitly; importing a module does not
implicitly import its nested modules.

Functions contained inside the module are available prefixed with the module's
name. They must always be called by their fully qualified names.

> Note: There is no way to "bring" a function to the current scope and use its
> unqualified name. Unqualified names are only available inside the immediate
> scope in which they are defined (i.e. functions may call other functions
> defined inside the same module by their unqualified names).
>
> Once again, this is caused by our extremely tight time budget.

A function may be called by its unqualified name only by functions defined in
the same module.
Functions defined in nested module do not automatically get access to functions
defined in outer modules. In order to use functions from the outer module the
nested module must import it.

Imports are always specified by the *full* path of the module, even when the
import is done from a nested module.

> Note: It is easier to implement this way. Time budget consideration.

----

### Example of how a module structure maps to filesystem structure

File: `A_module.lisp`

```
(module B_module)
(module Ax_module (
    ; Ax_module content
))
```

File: `A_module/B_module.lisp`

```
(module C_module)
```

File: `A_module/B_module/C_module.lisp`

```
(module D_module (
    ; D_module content
))
```

Given above files the source filesystem structure looks like this:

```
A_module.lisp
A_module/B_module.lisp
A_module/B_module/C_module.lisp
```

The output filesystem structure looks like this:

```
A_module.asm
A_module/B_module.asm
A_module/Ax_module.asm
A_module/B_module/C_module.asm
A_module/B_module/C_module/D_module.asm
```
