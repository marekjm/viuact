(import Std.Posix.Network)

(let main () {
    (let sock (Std.Posix.Network.socket))
    (print sock)
    (let cr (Io.close sock))
    (print cr)
    (let cr' (Io.wait cr))
    (print cr')
    0
})
