(import Kitchensink)

(let for_each_impl (v fn i limit) {
    (if (= i limit) 0 {
        (let each (Std.Vector.at v i))
        (fn each)
        (tailcall for_each_impl v fn (+ i 1) limit)
    })
})
(let for_each (v fn) {
    (let i 0)
    (let limit (Std.Vector.size v))
    (tailcall for_each_impl v fn i limit)
    0
})

(let repeat (n fn) (for_each (Kitchensink.make_vector n) fn))

(let ping_me_back (back n) {
    (let pinger (x) {
        (Std.Actor.send back x)
        0
    })
    (repeat n pinger)
})

(let receive_and_print () (print (Std.Actor.receive)))

(let main () {
    (let n 4)

    (actor ping_me_back (Std.Actor.self) n)

    (repeat n receive_and_print)

    0
})
