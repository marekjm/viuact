(import A_module)
(import B_module)

(module Nested_module)

(import Nested_module)
(import Nested_module.More_nested)

(let fn () {
    (print "Hello World! (from f)")
    (A_module.a_fn)
    (print "B from main")
    (B_module.b_fn)
    (Nested_module.fn)
    (Nested_module.More_nested.fn)
})

(let main () (fn))
