(module Example (
    (let call_me (x) (
        (print (x))
    ))
))

(import Example)
;(import A_module)

(let main () (
    (print ("Hello World!"))
    (Example.call_me ("Hello World!"))
))
