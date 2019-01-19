(import Std.Io)
(import Std.Posix.Network)

(let read_loop (sock) {
    (let client_prefix (Std.String.concat (Std.String.to_string sock) "> "))

    (try {
        (let message (Std.Posix.Network.read sock))
        (print (Std.String.concat client_prefix (Std.String.to_string message)))
        (tailcall read_loop sock)
    } (
        (catch Eof _ (print "the client sent EOF"))
        (catch Exception e {
            (print client_prefix)
            (print e)
            ; (print (Std.String.concat (Std.String.concat client_prefix "error: ") (Std.String.to_string e)))
            0
        })
    ))
    0
})

(let listen_loop (server_sock) {
    (print "server waits...")
    (let sock (Std.Posix.Network.accept server_sock))
    (print "accepted new client")

    (actor read_loop sock)

    (tailcall listen_loop server_sock)

    0
})

(let main (args) {
    (let server_sock (Std.Posix.Network.socket))

    (let interface (Std.String.to_string (Std.Vector.at args 1)))
    (print (Std.String.concat "running server on " interface))

    (Std.Posix.Network.bind server_sock interface 9090)
    (Std.Posix.Network.listen server_sock 16)

    (actor listen_loop server_sock)

    (Std.Io.stdin_getline)

    (Std.Posix.Network.shutdown server_sock)
    (Std.Posix.Network.close server_sock)

    0
})
