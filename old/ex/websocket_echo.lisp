(import Std.Posix.Network)
(import Websocket)

(let receive_message (client) {
    (try {
        (let message (Websocket.read client))
        message
    } ((catch Exception _ {
        (print "nothing received from WebSocket")
        (tailcall receive_message client)
    })))
})

(let main () {
    (let sock (Std.Posix.Network.socket))
    (Std.Posix.Network.bind sock "127.0.0.1" 9090)
    (Std.Posix.Network.listen sock 16)

    (let client (Std.Posix.Network.accept sock))
    (Websocket.handshake client)

    (let message (receive_message client))

    (Websocket.write client message)

    0
})
