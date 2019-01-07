(module A_module (
    (let f (parameter) (
        (print parameter)
    ))

    (module Nested_module (
        (let give_me_the_answer () (
            42
        ))
    ))
))

(module B_module)

(import A_module)
(import A_module.Nested_module)

(let g (n) (
    (let zero 0)
    (print n)
    (if (= n zero) 0 {
        (tailcall g (- n 1))
    })
))

(let main () (
    (actor A_module.f "Hello World!")

    (let s (struct))
    (:= s.answer {
        (print "Wow, I'm printed from inside an expression whose value will be")
        (print "assigned to a struct field. That's pretty rad!")
        (A_module.Nested_module.give_me_the_answer)
    })
    (print s)

    0
))
