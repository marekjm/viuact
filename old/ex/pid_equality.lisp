(let send_me_your_pid (reply_to) {
    (Std.Actor.send reply_to (Std.Actor.self))
    0
})

(let main () {
    (actor send_me_your_pid (Std.Actor.self))
    (let another_pid (Std.Actor.receive))
    (let this_pid (Std.Actor.self))
    (print (Std.Pid.eq this_pid this_pid))
    (print (Std.Pid.eq this_pid another_pid))
    0
})
