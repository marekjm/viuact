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

    ;
    ; PRINTER
    ;
    (let printer_loop (server) {
        (try {
            (let message (Std.Actor.receive 10s))
            (print (Std.String.concat "printer got: " (Std.String.to_string message.content)))
        } (
            (catch Exception _ (print "printer got nothing after 10 seconds"))
        ))
        (tailcall Print_protocol.printer_loop server)
        0
    })
    (let printer_impl (parent) {
        (Std.Actor.send parent (Std.Actor.self))

        (tailcall Print_protocol.printer_loop parent)

        0
    })
    (let start_printer () {
        (actor Print_protocol.printer_impl (Std.Actor.self))
        (let pid (Std.Actor.receive 5s))
        pid
    })

    ;
    ; SERVER
    ;
    (let server_loop (printer_pid) {
        (let message (Std.Actor.receive))
        (let message_type message.type)

        (if (= message_type 1) {
            (Std.Actor.send printer_pid message)
        } {
            0
        })

        (tailcall Print_protocol.server_loop printer_pid)
        0
    })
    (let server_impl (parent) {
        (Std.Actor.send parent (Std.Actor.self))

        (let printer_pid (start_printer))
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
    (echo "type something: ")
    (let message (Std.String.to_string (Std.Io.stdin_getline)))
    ; (print (Std.String.concat "got: " message))

    (Print_protocol.post_print server message)
    (tailcall loop server)

    0
})

(let main () {
    (let server (Print_protocol.start_server))
    (loop server)
    0
})
