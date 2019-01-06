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
    (print (fibonacci 0))   ; 0
    (print (fibonacci 1))   ; 1
    (print (fibonacci 4))   ; 3
    (print (fibonacci 6))   ; 8
    (print (fibonacci 14))  ; 377
))
