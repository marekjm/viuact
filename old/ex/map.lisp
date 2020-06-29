(import Kitchensink)

(let map_impl (acc v fn i limit) {
    (if (= i limit) acc {
        (let each (Std.Vector.at v i))
        (Std.Vector.push acc (fn each))
        (tailcall map_impl acc v fn (+ i 1) limit)
    })
})
(let map (v fn) {
    (let i 0)
    (let limit (Std.Vector.size v))
    (let acc (vector))
    (tailcall map_impl acc v fn i limit)
    0
})

(let times_2 (x) (* x 2))

(let main () {
    (let v (Kitchensink.make_vector 10))
    (print (map v times_2))
    0
})
