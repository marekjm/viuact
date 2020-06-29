(import Std.Posix.Network)

(let read_loop (sock) {
    (try {
        (print (Std.Posix.Network.read sock))
        (tailcall read_loop sock)
    } (
        (catch Eof _ (print "the client sent EOF"))
        (catch Exception _ 0)
    ))
    0
})

(let main (args) {
    (let server_sock (Std.Posix.Network.socket))

    (let interface (Std.String.to_string (Std.Vector.at args 1)))
    (print (Std.String.concat "running server on " interface))

    (Std.Posix.Network.bind server_sock interface 9090)
    (Std.Posix.Network.listen server_sock 16)

    (let sock (Std.Posix.Network.accept server_sock))
    (read_loop sock)

    (Std.Posix.Network.shutdown sock)
    (Std.Posix.Network.close sock)

    (Std.Posix.Network.shutdown server_sock)
    (Std.Posix.Network.close server_sock)

    0
})
