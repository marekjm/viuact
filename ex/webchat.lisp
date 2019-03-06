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

(let user_loop (client router) {
    (let message (receive_message client))

    (let received (struct))
    (:= received.event 2)
    (:= received.value message)
    (Std.Actor.send router received)

    (tailcall user_loop client router)
    0
})

(let user_establish (client router) {
    (Websocket.handshake client)

    (let register (struct))
    (:= register.event 1)
    (:= register.value (Std.Actor.self))
    (Std.Actor.send router register)

    (tailcall user_loop client router)
    0
})

(let accept_loop (sock router) {
    (let client (Std.Posix.Network.accept sock))
    (actor user_establish client router)
    (tailcall accept_loop sock router)
    0
})

(let send_to_all_clients (clients message) {
    (print clients)
    (print message)
    0
})

(let message_router_impl (clients) {
    (let msg (Std.Actor.receive))
    (if (= msg.event 1) {
        (Std.Vector.push clients (^ msg.value))
        (print clients)
        (tailcall message_router_impl clients)
    } (if (= msg.event 2) {
        (send_to_all_clients clients (^ msg.value))
        (tailcall message_router_impl clients)
    } (tailcall message_router_impl clients)))
})

(let message_router (back) {
    (let clients (vector))
    (Std.Actor.send back (Std.Actor.self))
    (tailcall message_router_impl clients)
    0
})

(let main () {
    (let sock (Std.Posix.Network.socket))
    (Std.Posix.Network.bind sock "127.0.0.1" 9090)
    (Std.Posix.Network.listen sock 16)

    (actor message_router (Std.Actor.self))
    (let router (Std.Actor.receive))

    (accept_loop sock router)

    0
})
