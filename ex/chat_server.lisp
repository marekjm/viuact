(import Std.Io)
(import Std.Posix.Network)

(let read_loop (sock) {
    (let client_prefix (Std.String.concat (Std.String.to_string sock) "> "))

    (try {
        (let message (Std.Posix.Network.recv sock 1000))
        (print (Std.String.concat client_prefix (Std.String.to_string message)))
        (tailcall read_loop sock)
    } (
        (catch Eof _ (print "the client sent EOF"))
        (catch Eagain _ (tailcall read_loop sock))
        (catch Exception e {
            (print (Std.String.concat
                client_prefix 
                (Std.String.to_string e)
            ))
            0
        })
    ))
    0
})

(let accept_loop (server_sock) {
    (print "[server][accept_loop] server waits...")
    (let sock (try (Std.Posix.Network.accept server_sock) (
        (catch Exception e {
            (print (Std.String.concat "[server][accept_loop] shutting down: " (Std.String.to_string e)))
            -1
        })
    )))
    (if (= sock -1) 0 {
        (print "[server][listen_loop] accepted new client")

        (actor read_loop sock)
        (print (Std.String.concat "[server][listen_loop] spawned an actor for client " (Std.String.to_string sock)))

        (tailcall accept_loop server_sock)
    })
})

(let main (args) {
    (let server_sock (Std.Posix.Network.socket))

    (let interface (Std.String.to_string (Std.Vector.at args 1)))
    (print (Std.String.concat "[server][main] running server on " interface))

    (Std.Posix.Network.bind server_sock interface 9090)
    (Std.Posix.Network.listen server_sock 16)

    (print "[server][main] press Enter to shutdown server")
    (try (actor accept_loop server_sock) (
        (catch Exception _ 0)
    ))

    (Std.Io.stdin_getline)

    (Std.Posix.Network.shutdown server_sock)
    (Std.Posix.Network.close server_sock)

    0
})
