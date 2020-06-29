(let main () {
    (let addition       (+ 1 2 3 4 5))
    (let subtraction    (- 1 2 3 4 5))
    (let multiplication (* 1 2 3 4 5))
    (let division       (/ 128.0 2 4 8))

    (print addition)
    (print subtraction)
    (print multiplication)
    (print division)

    (let logical_or  (or  true false 0.0 0))
    (let logical_and (and true false 1.0 1))

    (print logical_or)
    (print logical_and)

    0
})
