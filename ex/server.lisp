(import Std.Posix.Network)

(let main () {
    (let server_sock (Std.Posix.Network.socket))

    (Std.Posix.Network.bind server_sock "127.0.0.1" 9090)
    (Std.Posix.Network.listen server_sock 16)

    (let sock (Std.Posix.Network.accept server_sock))
    (print (Std.Posix.Network.read sock))

    (Std.Posix.Network.shutdown sock)
    (Std.Posix.Network.close sock)

    (Std.Posix.Network.shutdown server_sock)
    (Std.Posix.Network.close server_sock)

    0
})
