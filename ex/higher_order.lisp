(let call_this (f) {
    (f 42)
    0
})

(let is_the_integer_awesome (x) (if (= x 42) (print "Yes.") (print "No.")))

(let main () {
    (call_this is_the_integer_awesome)
    0
})
