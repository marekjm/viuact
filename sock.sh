#!/usr/bin/env bash

set -e

viuact-cc --mode exec ./sock.lisp
viuact-opt ./build/_default/sock.asm
viua-vm ./build/_default/sock.bc
