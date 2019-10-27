(let ratio (~num ~denom) (/ num denom))

(let main () {
    (print (ratio (~num 3.0) (~denom 4.0)))
    (print (ratio (~denom 4.0) (~num 3.0)))
    0
})
