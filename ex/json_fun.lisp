; Remember to clone and build the repository with JSON module. You can find it
; here: https://git.sr.ht/~maelkum/viua-stdjson

(import Std.JSON)

(let main () {
    (let s (struct))
    (:= s.message "Hello World!")
    (print s)
    (let jsonified (Std.JSON.to_json s))
    (print jsonified)
    (let again (Std.JSON.from_json jsonified))
    (print again)
    0
})
