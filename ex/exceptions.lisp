(let f () (/ 4 0))

(let main () {
    (let x (try (f) (
        (catch Zero_division e {
            (print "OH NOES, zero division happened!")
            1
        })
    )))
    (print x)
    0
})
