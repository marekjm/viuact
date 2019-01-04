(let main () (
    (let x (struct))
    (print x)

    (:= x.foo 42)
    (print x)

    (:= x.foo "Hello World!")
    (print x)
))
