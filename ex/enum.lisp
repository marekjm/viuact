(enum Examples (Foo Bar Baz))

(let main () {
    (print Examples.Foo)
    (print Examples.Bar)
    (print Examples.Baz)

    (let x Examples.Foo)
    (if (= x Examples.Bar) (print "It's a bar!") (print "It's not a bar..."))
    0
})
