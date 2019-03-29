(let make_vector_impl (v n limit) {
    (if (= n limit) v {
        (let m (+ n 1))
        (Std.Vector.push (^ v) n)
        (tailcall make_vector_impl v m limit)
    })
})
(let make_vector (limit) {
    (let i 0)
    (let v (vector))

    (make_vector_impl (Std.Pointer.take v) i limit)

    v
})

(let remove_integer_impl (acc v elem i limit) {
    (if (= i limit) acc {
        (let each (Std.Vector.at v i))
        (if (= each elem) 0 (Std.Vector.push acc each))
        (tailcall remove_integer_impl acc v elem (+ i 1) limit)
    })
})

(let remove_integer (v elem) {
    (let i 0)
    (let limit (Std.Vector.size v))
    (let acc (vector))
    (tailcall remove_integer_impl acc v elem i limit)
    0
})


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

(let main () {
    (let v (make_vector 10))
    (print v)
    (print (remove_integer (remove_integer v 4) 6))
    (print (filter v is_even_and_less_than_10))
    0
})
