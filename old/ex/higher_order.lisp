(let call_this_with (f n) {
    (f n)
    0
})

(let is_the_integer_awesome (x)
    (if (= x 42) (print "Yes.") (print "No.")))

(module Funky_module (
    (let call_me_a_zero (f) (f 0))
    (let i_will_tell_you_a_story (x) (print x))
))
(import Funky_module)

(let main () {
    ; The most basic example possible. We have a function and we feed
    ; that function another function to call.
    (call_this_with is_the_integer_awesome 42)

    (let fn is_the_integer_awesome)
    (let mapper call_this_with)
    (let arg -3)
    (mapper fn arg)

    (Funky_module.call_me_a_zero is_the_integer_awesome)
    (call_this_with Funky_module.i_will_tell_you_a_story
                    "Hello World!")

    (let shortcut Funky_module.i_will_tell_you_a_story)
    (call_this_with shortcut "Goodbye World!")

    0
})
