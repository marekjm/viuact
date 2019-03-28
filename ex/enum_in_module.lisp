(module Examples (
    (enum T (Foo Bar Baz))

    (let to_string (x)
        (if (= x T.Foo) "Examples.Foo"
        (if (= x T.Bar) "Examples.Bar"
        (if (= x T.Baz) "Examples.Baz" "Examples.T"))))
))

(import Examples)

(let main () {
    (print Examples.T.Foo)
    (print Examples.T.Bar)
    (print Examples.T.Baz)

    (print (Examples.to_string Examples.T.Foo))
    (print (Examples.to_string Examples.T.Bar))
    (print (Examples.to_string Examples.T.Baz))

    0
})
