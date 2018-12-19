(let fibonacci (n) (
    (if (= n 0) 0 {
        (if (= n 1) 1 {
            (let a (fibonacci (- n 1)))
            (let b (fibonacci (- n 2)))
            (+ a b)
        })
    })
))

(let main () (
    (print (fibonacci 0))
    (print (fibonacci 1))
    (print (fibonacci 4))
    (print (fibonacci 6))
    (print (fibonacci 14))
))
