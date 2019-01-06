(let make_struct () (
    (let x (struct))
    (:= x.inner (struct))
    (:= x.inner.value 41)
    x
))

(let main () (
    (let x (make_struct))
    (print x)

    (:= x.inner.value (+ x.inner.value 1))
    (print x)

    0
))
