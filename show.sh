#!/usr/bin/env bash

set -e

viuact-cc --version
viuact-cc --mode exec ./show.lisp
viuact-opt ./build/_default/show.asm
viua-vm ./build/_default/show.bc
