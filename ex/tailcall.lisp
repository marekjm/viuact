(let g () {
    (print "Hello World! (from g)")
    0
})

(let f () {
    (print "f() tail calls g()...")
    (tailcall g)
    (print "returned from g(), back in f()")
    0
})

(let main () {
    (f)
    0
})
