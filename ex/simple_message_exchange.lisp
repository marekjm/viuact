(let sender (receivers_pid message) (
    (print "sender: sends a message...")
    (Std.Actor.send receivers_pid message)
    (print "sender: sent a message...")
    0
))

(let receiver () (
    (print "receiver: waits for a message...")
    (let x (Std.Actor.receive))
    (print "receiver: got a message!")
    (print x)
    (print "receiver: done")
    0
))

(let main () (
    (let r (actor receiver))
    (sender r "Hello World!")
    (print "Hello XXX")
    0
))
