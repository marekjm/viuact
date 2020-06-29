; Import modules necessary for console and network I/O.
(import Std.Io)
(import Std.Posix.Network)

; Implement the algorithm used to find first occurence of a character in a
; string. This is needed to find newlines in message buffers.
;
; The find_first_impl() function is an implementation detail; find_first() is
; the "frontend" for this. The implementation detail function gets all needed
; state in the formal parameters whose starting values are supplied by the
; "frontend" function.
(let find_first_impl (haystack needle i limit) {
    ; If current index hit the limit we can just return -1 to signal that the
    ; character was not found.
    (if (= i limit) -1 {
        (let s (Std.String.at haystack i))
        ; If the character at current index is the needle return the index.
        ; Otherwise consider rest of the string recursively by tail calling the
        ; find_first_impl() function and passing updated state in parameters.
        (if (Std.String.eq s needle) i (tailcall find_first_impl haystack needle (+ i 1) limit))
    })
})
(let find_first (haystack needle) {
    ; Pass received arguments and the starting values for rest of the state
    ; needed by the function to work.
    (find_first_impl haystack needle 0 (Std.String.size haystack))
})


; The read loop is spawned in a separate actor for every accepted connection.
; This makes for a simple programming model. Required state is the client's
; socket and the remainder of the message buffer from the previous call.
(let read_loop (sock remainder) {
    (let client_prefix (Std.String.concat (Std.String.to_string sock) "> "))

    ; The read-and-print expression is executed inside a try to intercept
    ; exceptions that may be thrown by Std.Posix.Network.recv(); the network
    ; may fail, the client may disconnect, etc.
    (try {
        ; Here, we read what is available in the socket buffer in the OS,
        ; reading at most 1000 bytes.
        (let message (Std.Posix.Network.recv sock 1000))

        ; Messages in chat are delimited by newline (\n) characters. Since they may
        ; arrive fragmented (due to how network works) we have to combine the buffer we
        ; already have with the data that just arrived.
        (let message (Std.String.concat remainder (Std.String.to_string message)))

        ; Then, we need to find the end of the first message since we may have
        ; several messages inside our single buffer.
        (let end_of_message (find_first message "\n"))

        ; If end_of_message is -1 then we do not have any message inside the
        ; buffer. Let's just call ourselves recursively with the updated buffer
        ; passed as an argument.
        (if (= end_of_message -1) (tailcall read_loop sock message) {
            ; If we got a message, let's extract it from the buffer...
            (let m (Std.String.substr message 0 end_of_message))
            ; ...and cut it from the remainder (we do not want to print it
            ; twice).
            (let remainder (Std.String.substr message (+ end_of_message 1) (Std.String.size message)))

            ; Then, just print the received message, and try to fetch the next one.
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


; Accept loop is really simple. Just wait on the server socket for incoming
; connections and spawn an actor for every such received connection.
(let accept_loop (server_sock) {
    (print "[server][accept_loop] server waits...")

    ; This is an endless loop. If we encountered an error, just return -1 as
    ; the socket.
    (let sock (try (Std.Posix.Network.accept server_sock) (
        (catch Exception e {
            (print (Std.String.concat "[server][accept_loop] shutting down: " (Std.String.to_string e)))
            -1
        })
    )))

    ; If the socket is -1 this means that we need to shut down.
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
