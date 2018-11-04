(let main () (
    (let s "Hello World!")
    (print s)
    (let a 21)
    (let b 2)
    (print (* a b))
    (let c 2)
    (if (== c b) (
            (let s "Not true!")
            (print s)
        ) (
            (let s "Definitely true!")
            (print s)
        )
    )
))
