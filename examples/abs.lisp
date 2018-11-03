(let abs (x) (
    (let negative (< x 0))
    (if negative
        (* x -1)
        (x))
))

(let main () (
    (let a 2)
    (let b -3)
    (let b (abs b))
    (let c (+ a b))
    (let c_ptr (ref c))
    (print (deref c_ptr))
    0
))
