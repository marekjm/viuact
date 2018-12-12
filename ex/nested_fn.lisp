(let main () (
    (let nested (x) (
        (print x)
        (print "(from a nested function)")
    ))
    (nested "Hello World!")
))
