(let main () (
    ; This creates a vector.
    (let v (vector))
    (print v)

    ; Then let's push a simple primitive value to it. The Std.Vector.push
    ; function mutates the vector by pushing new values to the end of it.
    (Std.Vector.push v 42)
    (print v)

    ; Then, let's push a complex primitive value to the vector.
    ; The Std.Vector.push function returns a reference to the struct so we can
    ; immediately print it.
    (print (Std.Vector.push v (struct)))

    ; The Std.Vector.at function provides access to vector's elements. They are
    ; indexed using integers.
    (let element (Std.Vector.at v 1))
    (print element)

    ; Since we know the element was a struct, and structs can be mutated let's
    ; assign something to a field inside this struct.
    (:= element.foo 1)
    (print element)     ; We can see that the element was updated.
    (print v)           ; And (because Std.Vector.at returns a pointer to the
                        ; value inside a vector we also mutated the vector.

    0
))
