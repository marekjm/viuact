(module A_module (
    (let f (x) {
        (print x)
        (print "(from A_module.f)")
    })
))

; We need this import because functions are only implicitly visible
; inside their immediate surrounding scope.
; Imports of inline modules are not implicit.
(import A_module)

(let main () {
    (A_module.f "Hello World!")
})
