# Viuact language specification

This document presents Viua VM language specification.

- basic syntax
- basic and compound expressions
- let-binding (variable)
  - allowed variable names (`a` and `a'`)
- let-binding (function definition)
  - allowed parameter names (`a`, `a'`, and `~a`)
  - positional and labeled parameters (with label punning)
  - nested functions
  - closures
  - return values
- comments
- literals (int, float, text, struct, vector)
- simple and compound expressions (and their return values)
- *if* expression
- function call
- actor call
- tail call
- operator call
- struct field access
- enumerations (and custom field values)
- modules
  - inline modules
  - modules in separate files
  - imports
  - interface files
- exception handling

--------------------------------------------------------------------------------

# Basic syntax

The basic syntax of Viuact language is simple and inspired by the syntax (or
lack thereof) of the Lisp family of languages. It follows simple rules, and is
mostly consistent:

- every language structure is enclosed in parentheses
- everything if prefix notation

The first rule means that there will be many parentheses in your code, but is
there to make sure everything is clearly demarcated. The second rule is there to
make the recognition of language structure easier, and the flow of the language
more consistent:

    (leader_token other tokens following it)

The leader token is usually enough to identify the language structure you are
dealing with. For example:

    (let a 42)      ; let tells you this is a let-binding (variable definition)

    (if some_value  ; if tells you this is a conditional expression
        "If true."
        "If false.")

    (sqrt 2)        ; normal name as leader of the group tells you this is a
                    ; function call

It leads to one particularly surprising conclusion, though: the standard
mathematical operators also use prefix notation. There is also no operator
precedence table - everything is executed in the order of expressions in source
code.

    (* 2 2)         ; instead of 2 * 2, but still gives 4
    (* 2 (+ 1 3))   ; instead of 2 * (1 + 3), but still gives 8

One exception to the "everything infix" rule is struct, module, and enumeration
field access using "operator dot". It would be cumbersome (and too weird, and
more than a little bit unreadable) to write field accesses like this:

    (. (. some_struct foo) bar)

Instead, we stray from the infix path to let field accesses be written like
this:

    some_struct.foo.bar

This is much more readable so it's a good tradeoff.

## Comments

Comments are start with a semicolons (the `;` character), and end with the end
of the line on which they were started. There are no block comments. Consider
the example below:

    (let main () {
        ; (print "Hello, World!")
        0
    })

"Hello, World!" is not displayed because the call to the `print` function is
commented.

--------------------------------------------------------------------------------

# Basic expression types

Expressions can be simple or compound. A simple expression is...

- a literal (for a simple data type like an integer or a string)
- a constructor (for a complex data type like a struct or a vector)
- a function call (or an actor call)
- an operator call (e.g. division, addition, or pointer dereference)
- a conditional expression
- an exception catch expression

A compound expression is one or more expressions (simple or compound) enclosed
in braces, for example:

    (let a {            ; Bind the result of the compound expression to name a.
        (let x (fn 42)) ; Call a function and bind the result to name x,
        (print x)       ; then print it (e.g. for logging purposes).
        x               ; Return the value of x from the compound expression.
    })

The last value that is used in the compound expression is used as its return
value. Compound expressions can be nested to arbitrary levels.

These types of expressions (simple and compound) can appear on the left-hand
side of let-bindings. Using compound expressions allows building arbitrarily
complex expressions.

--------------------------------------------------------------------------------

# Let-bindings

Let-bindings are the means of tying values to names in Viuact. A let-binding may
be used to create a variable or a function. Since values are products of
evaluating expressions these two cases are not too different from each other - a
function is simply a parametrised expression whose evaluation is deferred until
the point of a function call, and which may be evaluated several times.

----------------------------------------

## Variables

    (let name expression)

A variable definition begins with the `let` keyword. A name follows it, and then
an expression which is immediately evaluated to produce a value that is bound to
the name.

Any legal expression may be used in the *expression* part of a
variable-defining let-binding: a literal, a constructor, a function call, a
conditional expression, etc. Some examples are provided below:

    (let the_answer 42)
    (let square_root_of_two (sqrt 2))
    (let what_do_you_say "Hello, World!")
    (let complexity_grows {
        (let evil 666)
        (print evil)
        evil
    })

Legal names for let-bindings follow this regular expression:

    ^([a-z][a-zA-Z0-9_]*'*|_)$

This means that regular names:

- must begin with a lowercase letter
- which can then be followed by a string of lower- and uppercase letters,
  digits, and underscore characters
- and may end with zero or more apostrophe characters

Alternatively, they may be a singular underscore character. This means *drop the
value*. If the compiler complains that a value is unused you may use the
following trick to silence it:

    (let _ unused_value)

The apostrophe characters at the end of a name are useful if you want to
create a slightly modified value but want to retain the untouched, previous
version of it:

    (let x (some_fn))
    (let x' (frobnicate x))

----------------------------------------

## Functions

    (let name (parameters) expression)

A function definition begins with the `let` keyword. A name follows it, then a
list of parameters (which may be empty), then the expression that represents the
body of the function. The expression is not immediately evaluated.

A function, in essence, is a parametrised expression whose evaluation is
suspended until a call point, and which may be evaluated zero or more times. In
case of non-referentially transparent functions the result of the evaluation may
differ each time (e.g. for functions returning time, random numbers, or bytes
read from a socket or file descriptor).

A function's return value is the value to which the expression representing its
body evaluates.

Any legal expression may be used as the function body. A few examples are
presented below:

    (let add_one (x) (+ x 1))

    (let print_and_return (x) {
        (print x)
        x
    })

    (let validate_answer (x) {
        (if (= x 42) x {
            (print "Your answer was not correct. Here, take a better one.")
            42
        })
    })

--------------------

### Function parameters

A function is a parametrised expression. The expression is parametrised by a set
of parameters. These are the names enclosed in parentheses that come before the
expression representing a function body.

Values to which these names are bound are supplied by the *caller* at the *call
point*. These values are called *arguments*.

In academic-speak, parameters are called *formal parameters* and arguments are
called *actual parameters*. To make it easier to remember: you state parameters,
but make arguments. In this documentation the informal nomenclature is used the
most.

In the example below, the function `fn` states two parameters: `a` and `b`.

    (let fn (a b) (+ a b))

To call it the caller has to make two arguments:

    (fn 23 19)

--------------------

#### Labeled parameters

By default the parameters are *positional*. This means that the arguments'
values are bound to them based on the order in which they are made. First
argument's value is bound to the first parameter, and so on.

Apart from positional parameters Viuact also supports labeled parameters. They
are useful in situations where the order of parameters is not intuitive, or when
a function is rarely used (so the users don't usually remember the order of
parameters) or when the function has many parameters (and it would be
impractical to rely on order alone).

Labeled parameters are marked by prending a *tilde* (the `~` character) to their
name in a function's parameter list. Inside the function body they are available
without the tilde, in the same way as positional parameters or let-bindings.
Consider the example below:

    (let ratio (~num ~denom) (/ num denom))

The numerator and denominator are labeled parameters. Viuact forces arguments to
be explicitly bound to labeled parameters. An explicit parameter bind means
enclosing a labeled name and its corresponding argument in parentheses. Consider
the example below:

    (ratio (~num 3.0) (~denom 4.0))

It is illegal to explicitly bind a positional parameter, or to implicitly pass a
labeled parameter.

Labeled arguments may be passed in any order and the compiler will ensure that
they are still bound to correct parameters. The calls in the example below will
produce the same results:

    (ratio (~num 3.0) (~denom 4.0))
    (ratio (~denom 4.0) (~num 3.0))

Viuact supports *label punning*, which lets the compiler automatically infer the
labeled parameter to which an argument should be bound if the argument is a name
that matches a labeled parameter name.

This feature is especially useful in situations where the arguments for the
function call are not made on the spot, but are stored in variables before
assembling in the finall call. Continuing with the `ratio` example:

    (let num (a_fn_to_get_the_numerator 1.41 3.14159 -1))
    (let denom {
        ; some complex calculations
    })
    (let result (ratio ~num ~denom))

To summarise, all calls in the next example produce are exactly the same:

    (let num 3.0)
    (let denom 4.0)

    (ratio (~num 3.0) (~denom 4.0))
    (ratio (~denom 4.0) (~num 3.0))     ; using a different order or arguments

    (ratio (~num num) (~denom denom))   ; using repetitive argument binds
    (ratio (~num denom) (~denom num))   ; explicit argument binds are possible

    (ratio ~num ~denom)                 ; using label punning
    (ratio ~denom ~num)

----------------------------------------

### Nested functions and closures

Viuact supports *nested functions*. They can be used to overcomplicate the
`ratio` example from the earlier section:

    (let ratio (~num ~denom) {
        (let divide (a b) (/ a b))
        (divide num denom)
    })

The `divide` function is defined and visible only inside the `ratio` function.
Nested functions are completely isolated from their surroundings (exactly like
non-nested functions) and communicate with their enclosing functions using the
normal caller-callee mechanisms (parameters, arguments, and return values).

Viuact also supports *closures*. The `ratio` example using closures would look
like this:

    (let ratio (~num ~denom) {
        (let divide () (/ num denom))
        (divide)
    })

Here, the `divide` function "inherits" both `num` and `denom` names and can
freely use them. However, closures only capture a *copy* of the names at the
closure's point of definition. If the variable is then mutated inside a closure
the outer function won't see the result, and vice versa.

--------------------------------------------------------------------------------

# Data types

Viuact supplies the programmer with a set of predefined data types that are
sufficient for the basic tasks. The data types are separated into two groups:

- simple data types (e.g. integer or float)
- compound data types (i.e. vector and struct)

Programmers can create their own data types using structs and vectors to add
structre to the data, and enumerations to add tags.

Viuact is dynamically (types are checked at runtime) and strongly (incompatible
types are not coerced) typed.

However, the strength of the type system stops at the predefined type boundary.
All user-defined types are just structs and vectors to the language. Another
weakness of the type system is that enumerations are not demarcated - if a
field of an enumeration has the same value as a field from another enumeration
they are considered the same.

Furthermore, all types, without exception, are implicitly convertible to a
boolean value.

A more accurate description of the typing discipline may then be dynamic and
semi-strongly typed.

----------------------------------------

## Simple data types

Simple data type has their own literal form (with some exceptions). Consider the
examples below:

- integer: `0`, `-1`, `42`
- float: `0.0`, `-1.0`, `4.2`
- string: `"Hello, World!"`
- boolean: `true` and `false`
- bytes: *no literal*
- pointers: *no literal*

A brief description of each simple data type is provided.

--------------------

### Numeric data types (integer and float)

Integers are 64 bit wide, two's complement signed values. They are stored in
byte order of the underlying platform.

Floats are double-precision IEEE 754 standard floating-point numbers.

Numeric types may be freely mixed in expressions, but the result of the
expression has the type of the left hand side element. This means that
multiplying a float by an integer will return a float, but dividing an integer
by a float will return an integer. Or, more formally:

    Mathematical_op : (Tlhs, Trhs) -> Tlhs

--------------------

### String

String data type is used to represent text in UTF-8 encoding. Strings are
sequences of Unicode codepoints, are indexed from 0, and are limited (in theory)
to 2^64 characters of length.

String literals are enclosed in double quotes (the `"` character). The usual
escape sequences are available to enter characters such as newline, tab, etc.

--------------------

### Boolean

Boolean data type is used to represent truth and false constants. Comparison
operators produce boolean values. Conditional expression consume boolean values
in their decision expression.

--------------------

### Bytes

Bytes are used to represent raw sequences of bytes. Bytes are unsigned, 8-bit
wide integers. Sequences of bytes are returned from sockets, and are passed in
parameters of the main function.

--------------------

### Pointer

A pointer is a means of accessing a value indirectly. No pointer literal or
constructor syntax is available - pointers are taken using the built-in
`Std.Pointer.take` function. Consider the example below:

    (let the_answer 42)
    (let answer_pointer (Std.Pointer.take the_answer))

To access the value to which the pointer points use the *pointer dereference*
operator:

    (print answer_pointer)      ; prints pointer representation
    (print (^ answer_pointer))  ; prints 42

----------------------------------------

## Compound data types

Compound data types are created using the constructor syntax. Their literals
have no special syntax sugar.

Compound data types are *mutable*. There are functions and operators that change
them in-place.

--------------------

### Vector

Vectors are sequences of values, indexed from 0. Here's how to create a vector:

    (let a_vector (vector))

The following built-in functions are available to operate on vectors:

- `Std.Vector.push`: takes a vector and a value. Returns a vector with the
  value pushed as the last element (the mutated vector taken as input).
- `Std.Vector.at`: takes a vector and an integer. Returns a pointer to the
  element at the specified index.
- `Std.Vector.size`: takes a vector. Returns an integer specifying the size
  of the vector.

An example:

    (let v (vector))
    (print v)                   ; prints []
    (Std.Vector.push v 42)
    (Std.Vector.push v 32)
    (Std.Vector.push v 666)
    (print v)                   ; prints [42, 32, 666]
    (let element (Std.Vector.at v 1))
    (print element)             ; prints 32 (due to automatic dereference)
    (print (^ element))         ; prints 32
    (print (Std.Vector.size v)) ; prints 3

--------------------

### Struct

Structs are key-value stores, where keys are legal, regular variable names and
values are any legal value. They have no other structure or limits. Fields are
added to structs dynamically.

Here's how to create a struct:

    (let a_struct (struct))

Here's how to assign a value to a struct's field:

    (:= a_struct.a_field 42)

Fields can be assigned to many times, thus mutating the struct.

#### Struct field access

Here's how to access a value in a struct's field:

    (print a_struct.a_field)
    (let x (+ a_struct.a_field 1))

The first expression in the struct field access may be any legal expression. All
following must be only regular field names. Consider the example below:

    (let s (struct))
    (:= s.field (struct))       ; Create a nested struct.
    (:= s.field.question "")    ; Assign a first value to a field.
    (:= s.field.question        ; Overwrite the value.
        "What's the meaning of Life, the Universe, and everything?")
    (:= s.field.answer 42)

    (let field s.field)         ; Bind the field pointer to a name.
    (print field)               ; Prints value of field due to automatic
                                ; dereference.
    (print (^ field))           ; Prints value of field because accessing a
                                ; struct returns a pointer.

    (print field.answer)        ; Direct access also works.
    (print (^ field).answer)    ; The same with explicit dereference.

More convoluted examples are also possible:

    (print (^ (Std.Pointer.take s)).field.answer)

    (print {
        (let s (struct))
        (:= s.also (struct))
        (:= s.also.works "Yeah, why not?")
        s
    }.also.works)

----------------------------------------

## Enumerations

Viuact supports enumerations as a means of assigning a symbolic meaning to some
opaque value. Values for enumeration fields are automatically selected.
Enumerations are created like this:

    (enum Animals (
        Reptiles
        Mammals
        Birds
        Fish
    ))
    (enum Food (
        Diary
        Meat
        Vegetables
        Fruit
        Fish
    ))

In theory, you should only rely on enumeration field's name and do not care
about its assigned value. In practice, you often do care about the assigned
value of an enumeration's field. In Viuact you can force a field to take on a
specific value:

    (enum Standard_streams (
        (Input 0)
        (Output 1)
        (Error 2)
    ))
    (enum Permission (
        (Read 4)
        (Write 2)
        (Execute 1)
    ))

Enumeration names must start with an uppercase letter. Enumeration field names
must start with an uppercase letter. Otherwise, they follow the rules for
regular variable names, except they cannot end in an apostrophe.

Enumeration fields are accessed using operator dot:

    (let r Permission.Read)
    (print r)                   ; prints 4

--------------------------------------------------------------------------------

# Conditional expressions

Viuact supports an *if-expression* as its only conditional expression. An if
expression is enclosed in parentheses and begins with the `if` keyword. The
keyword is the followed by *guard expression* and two *arms*: the first is
evaluated if the guard expression evaluates to truth, otherwise the second one
is evaluated. All three expressions (guard and arms) may be arbitrarily complex.

Consider the simple example below:

    (let answer (get_answer))
    (let is_correct (if (= answer 42) "Yep." "Nope."))

Or:

    (enum Part_of_day (Day Night))

    (let print_part_of_day (part) (if
        (= part Part_of_day.Day)        ; Guard expression.
        (print "What a sunny day!")     ; True arm.
        (print "What a cold night!")))  ; False arm.

If-expressions may be nested to make more complex decisions:

    (let orcish_integer_to_string (n)
        (if (= n 0)
            "None."
            (if (= n 1)
                "One."
                (if (= n 2)
                    "Two."
                    (if (<= n 5)
                        "Some."
                        "Many.")))))

--------------------------------------------------------------------------------

# Tail calls

----------------------------------------

## Simulating loops

--------------------------------------------------------------------------------

# Operators

----------------------------------------

## Carry-on operators

--------------------------------------------------------------------------------

# Actor system

----------------------------------------

## Spawning actors

--------------------

### Child actors

--------------------

### Free actors

----------------------------------------

## Communication using messages

--------------------------------------------------------------------------------

# Module system

--------------------------------------------------------------------------------

# Built-in functions

--------------------------------------------------------------------------------

# Compilation pipeline overview

--------------------------------------------------------------------------------

                        Copyright (c) 2019 Marek Marecki

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
