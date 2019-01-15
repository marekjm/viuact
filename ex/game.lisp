(import Std.Random)
(import Std.Io)

(let init (low high) {
    (let goal (Std.Random.randint low high))
    (let game (struct))
    (:= game.goal goal)
    game
})

(let guess_loop (game) {
    (echo "Enter your guess: ")
    (let guess (try (Std.Integer.of_bytes (Std.Io.stdin_getline)) (
        (catch Exception _ {
            (print "Your guess must be a number.")
            (tailcall guess_loop game)
        })
    )))

    (let goal game.goal)
    (if (= guess goal) {
        (print "You win!")
    } {
        (if (< guess goal) (print "Give me more!") (print "Give me less!"))
        (tailcall guess_loop game)
    })
    0
})

(let main () {
    (let game (init 1 100))
    (guess_loop game)
    0
})
