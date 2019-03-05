#!/usr/bin/env bash

# This file contains the exports of environment variables that are neccessary
# for correct operation of the Viuact compiler.

export VIUA_LIBRARY_PATH=../viuavm/build/stdlib:./lib:../libs/plain-websocket/build:../libs/viua-stdjson/build
export VIUAC_LIBRARY_PATH=$VIUA_LIBRARY_PATH

export VIUA_ASM_PATH=../viuavm/build/bin/vm/asm
export VIUA_VM_KERNEL_PATH=../viuavm/build/bin/vm/kernel
