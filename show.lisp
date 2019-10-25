(let ratio (~num ~denom) {
    (let divide (a b) (/ a b))
    (divide num denom)
})

(let ratio_closure (~num ~denom) {
    (let divide () (/ num denom))
    (divide)
})

(let mutating_closure () {
    (let x 0)
    (let fn () {
        (let _ x)
        (let x (+ x 1))
        0
    })

    (print x)
    (fn)
    (print x)

    0
})

(enum Example (
    Foo
    Bar
    Baz
))
(enum Field_assignment (
    (Answer 42)
    (Bar 32)
    (Evil 666)
))

(let main () {
    (let message "Hello, World!")
    (print message)

    (let num 3.0)
    (let denom 4.0)

    (print (ratio (~num 3.0) (~denom 4.0)))     ; 0.75
    (print (ratio (~denom 4.0) (~num 3.0)))     ; 0.75

    (print (ratio (~num num) (~denom denom)))   ; 0.75
    (print (ratio (~num denom) (~denom num)))   ; 1.33

    (print (ratio ~num ~denom))                 ; 0.75
    (print (ratio ~denom ~num))                 ; 0.75

    (print (ratio_closure ~num ~denom))         ; 0.75

    (mutating_closure)

    (print true)
    (print false)

    (let a 42)
    (let a_ptr (Std.Pointer.take a))
    (print a)
    (print a_ptr)
    (print (^ a_ptr))

    (let v (vector))
    (print v)
    (Std.Vector.push v 42)
    (Std.Vector.push v 32)
    (Std.Vector.push v 666)
    (print v)
    (let element (Std.Vector.at v 1))
    (print element)
    (print (^ element))
    (print (Std.Vector.size v))

    (let s (struct))
    (:= s.field (struct))
    (:= s.field.question (struct))
    (:= s.field.question "What's the meaning of Life, the Universe, and everything?")
    (:= s.field.answer 42)

    (let field s.field)
    (print field)
    (print (^ field))
    (print field.answer)
    (print (^ field).answer)
    (print (^ (Std.Pointer.take s)).field.answer)

    (print {
        (let s (struct))
        (:= s.also (struct))
        (:= s.also.works "Yeah, why not?")
        s
    }.also.works)

    (print Example.Foo)
    (print Example.Bar)
    (print Example.Baz)

    (print Field_assignment.Answer)
    (print Field_assignment.Bar)
    (print Field_assignment.Evil)

    0
})
