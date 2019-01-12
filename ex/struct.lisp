(let main () {
    ; Create and display empty struct.
    (let x (struct))
    (print x)

    ; Demonstrate simple struct field update.
    (:= x.foo 42)
    (print x)

    ; Demonstrate the fact that struct fields can be updated multiple
    ; times.
    (:= x.foo "Hello World!")
    (print x)
})
