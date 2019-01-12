(let f (x) {
    (print x)
    0
})

(let main () {
    (defer f "It's a message from the past... (from a deferred call)")
    (print "Hello World!")
    0
})
