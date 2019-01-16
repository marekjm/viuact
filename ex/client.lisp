(import Std.Io)
(import Std.Posix.Network)

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

        (echo "type your message: ")
        (Std.Posix.Network.write sock (Std.Io.stdin_getline))

        (Std.Posix.Network.shutdown sock)
        (print "shut down")

        (Std.Posix.Network.close sock)
        (print "closed")
    } 0)
    0
})
