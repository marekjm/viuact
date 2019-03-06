(import Std.Posix.Network)
(import Std.JSON)
(import Websocket)

(let receive_message (client) {
    (try {
        (let message (Std.JSON.from_json (Websocket.read client)))
        (print message)
        message
    } ((catch Exception _ {
        (print "nothing received from WebSocket")
        (tailcall receive_message client)
    })))
})

(let user_loop (client) {
    (let message (receive_message client))
    (Websocket.write client (Std.JSON.to_json message))
    (tailcall user_loop client)
    0
})

(let user_establish (client) {
    (Websocket.handshake client)
    (tailcall user_loop client)
    0
})

(let accept_loop (sock) {
    (let client (Std.Posix.Network.accept sock))
    (actor user_establish client)
    (tailcall accept_loop sock)
    0
})

(let main () {
    (let sock (Std.Posix.Network.socket))
    (Std.Posix.Network.bind sock "127.0.0.1" 9090)
    (Std.Posix.Network.listen sock 16)

    (accept_loop sock)

    0
})
