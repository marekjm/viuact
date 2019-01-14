(let f (a b) (/ a b))

(let main () {
    (let x (try (f 4 1) (
        (catch Zero_division _ {
            (print "zero division happened! returning 0")
            0
        })
    )))
    (print x)

    (let y (try (f 4 0) (
        (catch Zero_division _ {
            (print "zero division happened! returning 0")
            0
        })
    )))
    (print y)

    0
})
