(import B_module)

(let a_fn () {
    (print "Hello, A_module.a_fn(). Now, let's call B.")
    (B_module.b_fn)
})
