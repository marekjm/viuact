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
    (let msg (Std.Actor.receive (10s)))
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
    (print ((+ (a b))))

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
    (let ret_from_p (Std.Actor.join (p 1s)))
    (print (ret_from_p))

    (let print_pid (actor delayed_print ()))
    ;(let _ (actor delayed_print ()))
    (let msg "Hello World (after delay)!")
    (Std.Actor.send (print_pid msg))

    (let g (x) (
        (let h (x) (
            (print (x))
        ))
        (print ((+ (x 1))))
    ))

    (let n 41)
    (let z 1)
    (let k () (
        (print ((+ (n z))))
    ))
    (k ())

    (let _ 0)
))
