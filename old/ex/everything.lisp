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
    (let c (actor wrapping_enumerator 0 8))

    (Std.Actor.send c "Hello World! (0x0)")
    (Std.Actor.send c "Hello World! (0x1)")
    (Std.Actor.send c "Hello World! (0x2)")
    (Std.Actor.send c "Hello World! (0x3)")
    (Std.Actor.send c "Hello World! (0x4)")
    (Std.Actor.send c "Hello World! (0x5)")
    (Std.Actor.send c "Hello World! (0x6)")
    (Std.Actor.send c "Hello World! (0x7)")
    (Std.Actor.send c "Hello World! (0x8)")
    (Std.Actor.send c "Hello World! (0x9)")
    (Std.Actor.send c "Hello World! (0xa)")
    (Std.Actor.send c "Hello World! (0xb)")
    (Std.Actor.send c "Hello World! (0xc)")
    (Std.Actor.send c "Hello World! (0xd)")
    (Std.Actor.send c "Hello World! (0xe)")
    (Std.Actor.send c "Hello World! (0xf)")

    0
})
