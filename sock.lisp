(import Std.Posix.Network)

(let main () {
    (let sock (Std.Posix.Network.socket))
    (print sock)
    (let sock' (Std.Pointer.take sock))

    (let addr "127.0.0.1")
    (let port 16754)

    (Std.Posix.Network.bind sock' ~addr ~port)
    (Std.Posix.Network.listen sock' (~backlog 1))

    (print (Std.String.concat
        (Std.String.concat
            (Std.String.concat "Listening on " addr)
            ":")
        (Std.String.to_string port)))

    (let client (Std.Posix.Network.accept sock'))
    (print client)

    (print "reading...")
    (let rr (Io.read client 1000))
    (print rr)
    (let rr' (Io.wait rr))
    (print rr')

    (print "writing...")
    (let wr (Io.write client rr'))
    (print wr)
    (let wr' (Io.wait wr))
    (print wr')

    (print "closing client socket...")
    (let cr (Io.close client))
    (print cr)
    (let cr' (Io.wait cr))
    (print cr')

    (print "closing server socket...")
    (let cr (Io.close sock))
    (print cr)
    (let cr' (Io.wait cr))
    (print cr')
    0
})
