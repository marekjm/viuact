(let abs (x) (
    (let negative (< (x 0)))
    (print (negative))
    (if negative
        {
            (let n (* (x -1)))
            (print ("OK, it was a negative value."))
            n
        }
        x)
))

(let main () (
    (let i -3)
    (print (i))
    (print ((abs (i))))
    0
))
