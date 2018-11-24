(module Example (
    (let call_me (x) (
        (print (x))
    ))
))

(let main () (
    (print ("Hello World!"))
    (Example.call_me ("Hello World!"))
))
