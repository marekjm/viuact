#!/usr/bin/env bash

set -e

# CACT=viuact-cc
CACT=./cc.py
LACT=./opt.py

# export VIUACT_INFO=yes
# export VIUACT_VERBOSE=yes
# export VIUACT_DEBUGGING=yes

rm -rf ./build

echo "compiling: [module] B_module"
$CACT --mode module ./example/B_module.lisp
echo "compiling: [module] A_module"
$CACT --mode module ./example/A_module.lisp
echo "compiling: [ exec ] main"
$CACT --mode exec ./example/main.lisp

$LACT ./build/_default/main.asm
