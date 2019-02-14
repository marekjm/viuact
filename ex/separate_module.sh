#!/usr/bin/env bash

set -e

MODE=$1

if [[ $MODE == '' ]]; then
    echo "syntax: $0 ( make | run )"
    exit 0
fi

FILE_NAME=separate_module

if [[ $MODE == 'make' ]]; then
    echo "compiling dependencies of $FILE_NAME..."
    ./src/viuact-cc.py --mode module ex/External.lisp

    echo "compiling $FILE_NAME..."
    ./src/viuact-cc.py --mode exec ex/$FILE_NAME.lisp
    ./src/viuact-opt.py build/_default/$FILE_NAME.asm
fi
if [[ $MODE == 'run' ]]; then
    echo "running $FILE_NAME..."
    $VIUA_VM_KERNEL_PATH build/_default/$FILE_NAME.bc
fi
