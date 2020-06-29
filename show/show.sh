#!/usr/bin/env bash

set -e

viuact-cc --mode module ./Baz.lisp
viua-asm -Wunused-register -c -o ./build/_default/Baz.module ./build/_default/Baz.asm

viuact-cc --version
viuact-cc --mode exec ./show.lisp
viuact-opt ./build/_default/show.asm
viua-vm ./build/_default/show.bc
