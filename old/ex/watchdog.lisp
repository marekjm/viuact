; A watchdog is a normal function. It may contain arbitrary logic, call other
; functions, etc. The only things that make it different from ordinary
; functions are its extraordinary call circumstances, and the fact that any
; unhandled error encountered by the watchdog causes *immediate* process
; termination.
;
; A watchdog is the last line of defense against entering an uncontrolled
; failure mode where a process just crashes. It should be made extremely simple
; in order to reduce the chances that something inside the watchdog may go
; wrong. It is advised that you only use pure ViuAct code in watchdog as that
; gives the best reliability guarantees.
(let as_watchdog (crash_reason parent) {
    (print "process crashed")
    (Std.Actor.send parent crash_reason)
    0
})

(let as_process (parent) {
    ; Set watchdog as you would call a deferred function. The call does not
    ; return anything so do not pass the "result" to another function, and do
    ; not try to bind it.
    (watchdog as_watchdog parent)
    (let x (Std.Actor.receive 1st))
    (print x)
    0
})

(let main () {
    (actor as_process (Std.Actor.self))

    ; Here we await the message sent us by the watchdog. The actor that runs the
    ; "as_process" function is written to crash on purpose, so we *will* get the
    ; "crash message".
    (let a_message (Std.Actor.receive))
    (print a_message)

    0
})
