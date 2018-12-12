(let main () (
    ; A closure requires a variable that can be captured so let's create
    ; one.
    (let greeting "Hello World!")

    ; Then, a closure is needed.
    (let a_closure () (
        (print greeting)
        (print "(from a closure)")
    ))

    (a_closure)
))
