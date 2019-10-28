; Install Viua VM standard library first. Execute the following commands inside
; Viua VM repository:
;
;   make install PREFIX=~/.local
;   cp -Rv ./build/stdlib/Std/ ~/.local/lib/viuact/Std
;
; Assuming you have Viua VM standard library installed, execute the following
; commands to get this example to work:
;
;   export VIUACT_LIBRARY_PATH=~/.local/lib/viuact
;   export VIUA_LIBRARY_PATH=~/.local/lib/viua
;   viuact-cc --mode exec ./read.lisp
;   viuact-opt ./build/_default/read.asm
;   viua-vm ./build/_default/read.bc
;

(import Std.Posix.Io)

(enum Standard_streams (
    (Input 0)
    (Output 1)
    (Error 2)
))

(let main () {
    (let path "./read.lisp")
    (let file_fd (Std.Posix.Io.open ~path))
    (print file_fd)

    (let buffer_size 1000)
    (let line' (Io.read file_fd buffer_size))
    (let line (Io.wait line' 10s))

    (let out' (Io.write Standard_streams.Output line))
    (Io.wait out' 1s)

    0
})
