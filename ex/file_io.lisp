(import Std.Io)

(let main () {
    (let file "./ex/file_io.text")
    (let file (Std.Io.open file))
    (print (Std.Io.peek (Std.Pointer.take file)))
    (let contents (Std.Io.read (Std.Pointer.take file)))
    (print contents)
    (Std.Io.write (Std.Pointer.take file) contents)
    0
})
