; an inline module
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

; a non-inline module
(module X_module)

; imprting modules (even nested modules must be imported before use)
(import A_module.B_module)
(import A_module.B_module.C_module)
(import A_module.X_module)

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
    (A_module.X_module.drugs ())
))
