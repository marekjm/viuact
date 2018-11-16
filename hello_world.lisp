(module Std (
    (module Posix (
        (module Io (
            (let open (s) (
                s
            ))
        ))
    ))
))

(module Main (
    (let zero () (
        (let i 0)
    ))
    (let foo (x) (
        (print (x))
    ))
))

(let countdown (x) (
    (print (x))
    (if (= (x 0))
        x
        (countdown ((- (x 1))))
    )
))

(let main () (
    (let s "Hello World!")
    (Main.foo (s))
    (let i (Main.zero ()))
    (print (i))
    (let x (Std.Posix.Io.open ("./foo.asm")))
    (print (x))

    (let a 1)
    (let b 41)
    (let c (+ (a b)))
    (print (c))

    ;(if (= (c 43))
    ;    (print ("Hell, yes!"))
    ;    (print ("Hell, no!"))
    ;)

    ;(let msg (if (= (c 42))
    ;    "Oh yeah..."
    ;    "OH NOES!"
    ;))
    ;(print (msg))

    ;(print ((if (= (c 42))
    ;    "X"
    ;    "Y"
    ;)))

    (countdown (10))

    (let _ 0)
))
