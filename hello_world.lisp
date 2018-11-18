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

(let delayed_print () (
    (print ("delayed_print() awaiting a message..."))
    (let msg (receive (10s)))
    (print (msg))
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

    (let p (actor countdown (10)))
    (print (p))
    (let ret_from_p (join (p 1s)))
    (print (ret_from_p))

    ;(let print_pid (actor delayed_print ()))
    (let _ (actor delayed_print ()))
    ;(let msg "Hello World (after delay)!")
    ;(send (print_pid msg))

    (let _ 0)
))
