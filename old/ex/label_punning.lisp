(let ratio (~num ~denom) (/ num denom))

(let main () {
    (let num 3.0)
    (let denom 4.0)

    (print (ratio ~num ~denom))
    (print (ratio ~denom ~num))
    0
})
