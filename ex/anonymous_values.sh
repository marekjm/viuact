#!/usr/bin/env bash

set -e

MODE=$1

if [[ $MODE == '' ]]; then
    echo "syntax: $0 ( make | run )"
    exit 0
fi

FILE_NAME=anonymous_values

if [[ $MODE == 'make' ]]; then
    echo "compiling $FILE_NAME..."
    ./cc.py --mode exec ex/$FILE_NAME.lisp
    ./opt.py build/_default/$FILE_NAME.asm
fi
if [[ $MODE == 'run' ]]; then
    echo "running $FILE_NAME..."
    $VIUA_VM_KERNEL_PATH build/_default/$FILE_NAME.bc
fi
