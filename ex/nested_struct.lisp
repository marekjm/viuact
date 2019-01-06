(module Foo (
    (let make (message) (
        (let x (struct))
        (:= x.inner (struct))
        (:= x.inner.most (struct))

        ; Display the ability to assign a value to a field inside a nested
        ; struct.
        (:= x.inner.most.bar message)

        x
    ))
))

(import Foo)

(let main () (
    (let x (Foo.make "Hello World!"))
    (print x)
))
