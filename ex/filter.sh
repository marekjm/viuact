#!/usr/bin/env bash

set -e

MODE=$1

if [[ $MODE == '' ]]; then
    echo "syntax: $0 ( make | run )"
    exit 0
fi

FILE_NAME=filter

if [[ $MODE == 'make' ]]; then
    echo "compiling dependencies of $FILE_NAME..."
    ./cc.py --mode module ex/Kitchensink.lisp

    echo "compiling $FILE_NAME..."
    ./cc.py --mode exec ex/$FILE_NAME.lisp
    VIUAC_ASM_FLAGS='-Wunused-value' ./opt.py build/_default/$FILE_NAME.asm
fi
if [[ $MODE == 'run' ]]; then
    echo "running $FILE_NAME..."
    $VIUA_VM_KERNEL_PATH build/_default/$FILE_NAME.bc ${@:2}
fi
