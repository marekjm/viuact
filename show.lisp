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
(enum Part_of_day (Day Night))

(let print_part_of_day (part) (if
    (= part Part_of_day.Day)
    (print "What a sunny day!")
    (print "What a cold night!")))

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

(let for_each_impl (v i fn) {
    (if (< i (Std.Vector.size v)) {
        (let each (Std.Vector.at v i))
        (fn each)
        (tailcall for_each_impl v (+ i 1) fn)
    } 0)
})
(let for_each (v fn)
    (tailcall for_each_impl v 0 fn))

(module Foo (
    (let fn (~x) (print x))
))
(import Foo)

(module Bar)
(import Bar)

(import Baz)

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

    (print_part_of_day Part_of_day.Night)

    (print (orcish_integer_to_string 0))
    (print (orcish_integer_to_string 1))
    (print (orcish_integer_to_string 2))
    (print (orcish_integer_to_string 3))
    (print (orcish_integer_to_string 5))
    (print (orcish_integer_to_string 6))
    (print (orcish_integer_to_string 666))

    (let printer (x) (print x))
    (for_each v printer)

    (Foo.fn (~x "Hello, World!"))
    (Bar.fn (~x "Hello, World!"))
    (Baz.fn (~x "Hello, World!"))

    0
})
