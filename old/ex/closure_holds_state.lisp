(let main () {
    ; Let's create a counter that the closure will capture.
    (let i 0)

    ; Then, create a closure.
    (let a_stateful_closure () {
        ; This is needed to make the compiler notice that the i variable
        ; is captured by this function. It has problems with detecting
        ; captures inside nested expressions.
        (let _ i)   

        ; Increase the counter.
        (let i (+ i 1))

        ; Return the counter decreased by 1, as we want to return the
        ; same value we started with (we are a counter from N to
        ; infinity).
        (- i 1)
    })

    (print (a_stateful_closure))
    (print (a_stateful_closure))
})
