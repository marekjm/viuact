(import Std.Io)
(import Std.Posix.Network)

(let find_first_impl (haystack needle i limit) {
    (if (= i limit) -1 {
        (let s (Std.String.at haystack i))
        (if (Std.String.eq s needle) i (tailcall find_first_impl haystack needle (+ i 1) limit))
    })
})
(let find_first (haystack needle) {
    (find_first_impl haystack needle 0 (Std.String.size haystack))
})

(let read_loop (sock remainder) {
    (let client_prefix (Std.String.concat (Std.String.to_string sock) "> "))

    (try {
        (let message (Std.Posix.Network.recv sock 1000))
        (let message (Std.String.concat remainder (Std.String.to_string message)))

        (let end_of_message (find_first message "\n"))

        (if (= end_of_message -1) (tailcall read_loop sock message) {
            (let m (Std.String.substr message 0 end_of_message))
            (let remainder (Std.String.substr message (+ end_of_message 1) (Std.String.size message)))

            (print (Std.String.concat client_prefix m))

            (tailcall read_loop sock remainder)
        })
    } (
        (catch Eof _ (print "the client sent EOF"))
        (catch Eagain _ (tailcall read_loop sock remainder))
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

        (actor read_loop sock "")
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
