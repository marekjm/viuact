(let countdown (n) {
    (let x (try (Std.Actor.receive 1s) (
        (catch Exception _ (tailcall countdown n))
    )))

    (let wrapped (struct))
    (:= wrapped.value x)
    (:= wrapped.sequence (Std.copy n))
    (actor f wrapped)

    (if (= n 0) 0 (tailcall countdown (- n 1)))
})

(let wrapping_enumerator (n top) {
    (let x (try (Std.Actor.receive 1s) (
        (catch Exception _ (tailcall wrapping_enumerator n top))
    )))

    (let n (if (= n top) 0 n))

    (let wrapped (struct))
    (:= wrapped.value x)
    (:= wrapped.sequence (Std.copy n))
    (actor f wrapped)

    (tailcall wrapping_enumerator (+ n 1) top)
    0
})

(let f (x) (print x))

(let main () {
    (let c (actor wrapping_enumerator 0 2))

    (Std.Actor.send c "Hello World! (0)")
    (Std.Actor.send c "Hello World! (1)")
    (Std.Actor.send c "Hello World! (2)")
    (Std.Actor.send c "Hello World! (3)")
    (Std.Actor.send c "Hello World! (4)")

    0
})
