# Viua Lisp

Expression-based language.
Functional and statically typed.

Compiled by converting the source code into a series of high-level
abstract instructions (e.g. let-binding, ctor-op, call-op, etc.)
modelling the flow of execution and data in a SSA-based regime.
Most of these abstract ops are tuples of `(op, output-slot, input-slot*)`.
The abstract ops are then "lowered" into (or: compiled) the Viua VM
assembly language.

This conversion is pretty straightforward, and for programmers
proficient in both Viua VM asm and Lisp it should not be difficult
to map portions of generated asm to original source code.

Viua Lisp is *not* type checked.
It leverages Viua VM assembler's type checking and static analysis
capabilities to perform compile-time verification.

The language sports few mechanisms, with syntax oriented arund RPN
with no special case for arithmetic operators. Functions are not
automatically curried - each must be called with a tuple containing
all its arguments. Currying can be implemented manually.

----

# Expressions

This is a list of expressions supported by Viua Lisp.

## Let bindings

    (let x ...)
    
Normally, the `(...)` expression would be assigned an anonymous slot and
used immediately by some other expression. The `let x` just gives a
name to the slot assigned to the would-be-anonymous expression.

Names must match the following regex: `^[a-z][A-Za-z0-9_]*'*$`. Names
beginning with `_` are reserved.

Viua lisp allows name rebinding, i.e. this code is valid:

    (let x 42)
    (let x "Hello World!")
    
## Mutable let bindings

    (let mutable x ...)
    
Values are immutable by default. The `mutable` keyword marks the value
to which the binding is made as mutable.

Well... I lied. The values *are* in fact mutable in the underlying model
that is provided by Viua VM. However, Viua Lisp enforces on programmers a
view that the values are immutable. The `mutable` keyword just casts this
illusion away.

## Static let bindings

    (let static x ...)
    
Values use the "local" lifetime by default. The `static` keyword changes
that and makes the value use "static" lifetime.

**Implementation note**: "local" lifetime means using of `local` register
set; "static" lifetime means using the `static` register set.

## `(...)` vs `...`

Adding extra parentheses may sometimes change the meaning of an expression.
For example, function *calls* must be wrapped in parentheses, otherwise they
are just references to function's name.

## Literals

     0
    -0
     0.0
    -0.0
     0b01
     0x0123456789abcdef
    "Hello World!"
    true
    false

Basic types (those that have literals) are:

- signed integer
- double
- bits
- string
- boolean

Integers and doubles are platform-dependent.
Strings are UTF-8 encoded.
Bits are arbitrary width, and used to perform bit operations as well
as platform-independent arithmetic (checked, wrapping, saturating).

## Function definitions

    (let f (x) ...)
    
Functions are parameterised expressions. A function's formal parameters
must be wrapped in parentheses.

## Compound expressions

    { ... }

A compound expression may be supplied wherever a simple expression is
expected. Its return value is the value of the last expression of the compound
expression.

## Module definitions

    (module Module (...))
    
Modules are collections of functions.
The only expression type allowed inside a module's body is a function definition.
Module names must begin with a capital letter, and match the following regex: `^[A-Z][A-Za-z0-9_]$`.

## Compound type literals

Compound types are types that do not have "primitive" literals (like
the basic types), and have to be constructed using a function call-like
syntax.

**Implementation note**: They also compile to multiple to multiple
instructions instead of just one instruction (like basic types do).

### Tuples

    (tuple (42 "Hello World!"))

A sequence of values with possibly differing types.

### Vectors

    (vector (0 1 2))

A series of values with the same type.

### Structs

    (struct (
        (foo 42)
        (bar "Hello World!")
    ))

A key-value mapping, structs are a series of `(<name> (...))` pairs.

## Function calls

    (let f (x y z) (...))
    (f (42 2018 0))
    
    (<name> (<expr>*))

Why is the extra parentheses needed around function arguments?
First, to match the way a function is defined:

    (let f (x y z) (...))   ; a definition
        (f (0 1 2))         ; a call

And second, to remove ambiguities. Consider the following cases:

    (let x (f))         ; Is `x` a result of a call to `f`?
                        ; Or a different name for `f`?

In theory, the requirement for the call to be wrapped with parentheses
removes the ambiguity:

    (let f' f)      ; `f'` is another name for `f`.
    (let x (f))     ; `x` is the result of a call to `f`.
    
But this conflicts with the rule that "additional parentheses do not change
the meaning of an expression". Consider:

    (let f' (f))    ; Oh no, we added a parentheses and now it's a call!

Also, this kinda conflicts with compound types constructor syntax:

    (let a 42)
    (let b (tuple (a 1)))
                ; ^^^^^ is this a call? No, it's a ctor that creates a tuple
                ; of two integers: (42, 1)
    
    (let c (vector (a 1 2))
                 ; ^^^^^^^ is this a call?

This ambiguity is present only if we do not look at the surrounding tokens
when parsing such an expression. If we see just `(f x y)` we don't know whether
it's a plain call of a part of a tuple ctor. But if we allow ourselves to look
around, just a little bit even, we can clearly see that... `(tuple (f x y))` it
*is* in fact a tuple ctor!

For a recursive descent parser this is easy to disambiguate, as it can just expect
a sequence of expressions enclosed in parentheses. Even a shift-reduce parser would
not have many difficulties with this, with a production like this one:

    TupleCtor          := Open_paren 'tuple' Tuple_args Close_paren
    'tuple' Tuple_args := 'tuple' Open_paren Expr* Close_paren

So I'm not really sure if adding the extra parentheses really does solve anything.
We don't need any "extra" information about the *meaning* of the tokens, just the
token sequence itself to disambiguate, so we should be context-free.

## Access to fields of compound types

    (let x (tuple (42 "Hello World!")))
    (let a (Tuple.at x 1))  ; a is now "Hello World!"

Fields of tuples are accessed using the built-in module `Tuple`.

    (let x (vector (2 3 4)))
    (let a (Vector.at x 0)) ; a is now 2

Fields of vectors are accessed using the built-in module `Vector`.

    (let x (struct (
        (foo 42)
        (bar "Hello World!")
    ))
    (let a (. x foo))       ; a is now 42
                            ; The dot (`.`) is a normal operator, with usual semantics.

Fields of structs are accessed using the `.` operator.
