(let main () (
    (let x (struct))
    (:= x.inner (struct))
    (:= x.inner.most (struct))
    (print x)

    (:= x.inner.most.value 41)
    (print x)

    (print x.inner.most.value)
    (print (+ x.inner.most.value 1))

    (let z x.inner.most.value)
    (print z)

    0
))
