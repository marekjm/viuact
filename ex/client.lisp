(import Std.Io)
(import Std.Posix.Network)

(let write_loop (sock) {
    (echo "type your message: ")
    (let message (Std.Io.stdin_getline))

    (if message (try {
            (Std.Posix.Network.write sock message)
            (tailcall write_loop sock)
        } (
            (catch Exception _ 0)
        )) 0)
    0
})

(let main () {
    (let sock (Std.Posix.Network.socket))
    (print (Std.String.concat "created a socket: " (Std.String.to_string sock)))

    (let connected (try { (Std.Posix.Network.connect sock "127.0.0.1" 9090) true } (
        (catch Exception _ {
            (print "failed to connect")
            false
        })
    )))

    ; FIXME name reference in if condition trigger an unnecessary copy
    (if connected {
        (print "connected to 127.0.0.1:9090")

        (write_loop sock)

        (Std.Posix.Network.shutdown sock)
        (print "shut down")

        (Std.Posix.Network.close sock)
        (print "closed")
    } 0)
    0
})
