(module Print_protocol (
    ; This is a module that abstracts away the complexity of managing concurrent
    ; echo server. Due to the fact that Viuact does not provide any error
    ; recovery facilities yet, we have to rely on deferred calls and indirection
    ; to manage a facade of fault resistancy.
    ;
    ; However, the error handling strategy developed here seems wierdly
    ; appropriate for Viuact.

    (let make_dead () {
        ; Create the "printer died" message.

        (let message (struct))
        (:= message.type 0)
        message
    })
    (let make_print (value) {
        ; Create the "print this" message.

        (let message (struct))
        (:= message.type 1)
        (:= message.content value)
        message
    })
    (let post_print (server message) {
        (let message (make_print message))
        (Std.Actor.send server message)
        server
    })
    (let make_shutdown () {
        ; Create the "shutdown" message.

        (let message (struct))
        (:= message.type 2)
        message
    })

    (let server_loop (printer_pid) {
        (print "server waits for messages...")
        (let message (Std.Actor.receive))
        (print message.type)
        (tailcall Print_protocol.server_loop printer_pid)
        0
    })
    (let server_impl (parent) {
        (Std.Actor.send parent (Std.Actor.self))

        (let printer_pid (Std.Actor.self))
        (tailcall Print_protocol.server_loop printer_pid)

        0
    })
    (let start_server () {
        (actor Print_protocol.server_impl (Std.Actor.self))
        (let pid (Std.Actor.receive 1s))
        pid
    })
    (let stop_server (server) {
        (Std.Actor.send server (make_shutdown))
        0
    })
))

(import Print_protocol)
(import Std.Io)

(let loop (server) {
    (print "type something:")
    (let message (Std.String.to_string (Std.Io.stdin_getline)))
    (print (Std.String.concat "got: " message))

    (Print_protocol.post_print server message)
    (tailcall loop server)

    0
})

(let main () {
    (print "running: 0001")

    (let server (Print_protocol.start_server))

    (loop server)

    (print "Hello World! (after loop, from main)")

    (print "main() exited")
    0
})
