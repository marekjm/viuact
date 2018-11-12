(module Main (
    (let zero () (
        (let i 0)
    ))
    (let foo (x) (
        (print (x))
    ))
    (let main (args) (
        (let s "Hello World!")
        (foo (s))
        (zero ())
        ;(let i 42)
        ;(let i_neg -42)
        ;(let f 4.2)
        ;(let f_neg -4.2)
        ;(let f_dec .2)
        ;(let f_dec_neg -.2)
        ;(let x (struct ()))
        ;(let x (vector (0 1 2)))
        ;(print s)
        ; (let a 21)
        ;(let b 2)
        ;(print (* a b))
        ;(let c 2)
        ;(if (== c b) (
        ;        (let s "Not true!")
        ;        (print s)
        ;    ) (
        ;        (let s "Definitely true!")
        ;        (print s)
        ;    )
        ;)
    ))
))
