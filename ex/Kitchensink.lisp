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
