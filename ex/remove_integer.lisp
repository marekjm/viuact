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

(let main () {
    (let v (make_vector 10))
    (print v)
    (print (remove_integer (remove_integer v 4) 6))
    0
})
