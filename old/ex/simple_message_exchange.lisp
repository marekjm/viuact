; Viuact actors (implemented as Viua VM processes) are isolated from each other
; and communicate exclusively via message passing. Message passing in Viuact is:
;
;   - asynchronous: an actor does not wait for the other side to receive sent
;     messages
;   - direct: an actor sends a message directly to the other actor's message
;     queue without any intermediate channels, queues, etc.
;   - without any guarantees of delivery
;   - without any guaranetees on the order of messages
;
; These limitations are due to the way physical world works. Messages *may* get
; lost, delayed, or arrive out of order. Instead of trying to work around them
; on a system level Viuact provides tools to implement protocols with desired
; level of reliability in "user space".
;
; These "tools" are timeouts on operations that may block for an unlimited
; amount of time, e.g. receiving a message. An actor may specify a value in
; seconds or milliseconds that is the maximum amount of time it wants to wait
; for an event to happen. Timeouts may be specified for two operations:
;
;   - Std.Actor.receive: when an actor receives a message
;   - Std.Actor.join: when an actor wants to wait for another actor to finish
;     execution
;
; Timeouts let the programmer compose software that gives soft guarantees about
; the maximum time it will take for an operation to finish no matter what the
; "outside world" is doing. These guarantees are limited to the parts of the
; software that are compiled to Viua VM bytecode and run by its scheduler. Code
; written in C++ modules only gives as strong guarantees as the programmer
; writing it could ensure - but this is a neccessary price to pay for the
; interaction with environment outside of the VM.
;

(let sender (receivers_pid message) {
    ; The sender sends a message to the specified PID.
    ;
    ; In this example sender() is just a helper function used to wrap the send
    ; operation in a pair of prints to display the approximate order of events
    ; (messages being sent and received) to the human watching the software run.
    (print "sender: sends a message...")
    (Std.Actor.send receivers_pid message)
    (print "sender: sent a message!")
    0
})

(let receiver () {
    ; The receiver waits for a message to arrive to its message queue.
    ;
    ; As with sender(), in this example receiver() is just a helper function
    ; that wraps the "message received" event in a pair of prints.
    (print "receiver: waits for a message...")
    (let x (Std.Actor.receive))
    (print "receiver: got a message!")
    (print (Std.String.concat "receiver: the message was: " (Std.String.to_string x)))
    0
})

(let main () {
    (let r (actor receiver))
    (sender r "Hello World!")
    0
})
