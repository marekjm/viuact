#!/usr/bin/env bash

set -e

MODE=$1

if [[ $MODE == '' ]]; then
    echo "syntax: $0 ( make | run )"
    exit 0
fi

FILE_NAME=timeout

if [[ $MODE == 'make' ]]; then
    echo "compiling $FILE_NAME..."
    ./src/viuact-cc.py --mode exec ex/$FILE_NAME.lisp
    ./src/viuact-opt.py build/_default/$FILE_NAME.asm
fi
if [[ $MODE == 'run' ]]; then
    echo "running $FILE_NAME..."
    VIUA_ENABLE_TRACING=yes gdb --args ../core/viuavm/build/bin/vm/kernel build/_default/$FILE_NAME.bc
    # gdb --args ../core/viuavm/build/bin/vm/kernel build/_default/$FILE_NAME.bc
    # ../core/viuavm/build/bin/vm/kernel build/_default/$FILE_NAME.bc
fi