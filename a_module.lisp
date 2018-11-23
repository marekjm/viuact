(module B_module (
    (module C_module (
        (let grill () (
            (print ("Let's eat"))
        ))
    ))
    (let bar () (
        (print ("Let's drink!"))
    ))
))

(import A_module.B_module)
(import A_module.B_module.C_module)

(let foo (x) (
    (let adder (a b) (
        (+ (a b))
    ))
    (adder (x 1))
))

(let fn (x) (
    (print (x))
    (foo (41))
    (A_module.B_module.bar ())
    (A_module.B_module.C_module.grill ())
))
