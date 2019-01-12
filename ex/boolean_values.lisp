(let main () {
    (let bt true)
    (let bf false)

    (print bt)
    (print bf)

    (print "not:")
    (print (not true))
    (print (not false))

    (print "or:")
    (print (or false false))
    (print (or false true))
    (print (or true  false))
    (print (or true  true))

    (print "and:")
    (print (and false false))
    (print (and false true))
    (print (and true  false))
    (print (and true  true))

    0
})
