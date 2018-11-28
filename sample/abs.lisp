(let abs (x) (
    (let negative (< (x 0)))
    (print (negative))
    (if negative
        (* (x -1))
        x)
))

(let main () (
    (let i -3)
    (print (i))
    (print ((abs (i))))
    0
))
