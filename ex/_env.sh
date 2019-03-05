#!/usr/bin/env bash

# This file contains the exports of environment variables that are neccessary
# for correct operation of the Viuact compiler.

export VIUA_LIBRARY_PATH=../core/viuavm/build/stdlib:./lib:../libs/websocket/build
export VIUAC_LIBRARY_PATH=../core/viuavm/build/stdlib:./lib:../libs/websocket/build
export VIUA_VM_KERNEL_PATH=../core/viuavm/build/bin/vm/kernel
