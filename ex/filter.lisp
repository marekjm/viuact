; The classic filter function that everybody knows and admires.
; Now, written in ViuAct! Order yours for just $5
(let filter_impl (acc v fn i limit) {
    (if (= i limit) acc {
        (let each (Std.Vector.at v i))
        (if (fn each) (Std.Vector.push acc each) 0)
        (tailcall filter_impl acc v fn (+ i 1) limit)
    })
})
(let filter (v fn) {
    (let i 0)
    (let limit (Std.Vector.size v))
    (let acc (vector))
    (tailcall filter_impl acc v fn i limit)
    0
})

(let is_even_and_less_than_10 (x) (or
    (or (= x 2) (= x 4))
    (or (= x 6) (= x 8))
))

(import Kitchensink)

(let main () {
    (let v (Kitchensink.make_vector 10))
    (print (filter v is_even_and_less_than_10))
    0
})
