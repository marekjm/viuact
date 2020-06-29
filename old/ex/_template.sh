#!/usr/bin/env bash

set -e

MODE=$1

if [[ $MODE == '' ]]; then
    echo "syntax: $0 ( make | run )"
    exit 0
fi

FILE_NAME=_template

if [[ $MODE == 'make' ]]; then
    echo "compiling $FILE_NAME..."
    viuact cc --mode exec ex/$FILE_NAME.vt
    viuact link build/_default/$FILE_NAME.asm
fi
if [[ $MODE == 'run' ]]; then
    echo "running $FILE_NAME..."

    if [[ $VIUA_VM_KERNEL_PATH == '' ]]; then
        VIUA_VM_KERNEL_PATH=viua-vm
    fi
    $VIUA_VM_KERNEL_PATH build/_default/$FILE_NAME.bc ${@:2}
fi
