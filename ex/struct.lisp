(let main () (
    (let x (struct))
    (print x)

    (:= x.inner (struct))
    (print x)

    (:= x.inner.most (struct))
    (print x)

    (:= x.inner.most.bar "Hello (inner) World!")
    (print x)

    (:= x.foo 42)
    (print x)

    (:= x.foo "Hello World!")
    (print x)
))
