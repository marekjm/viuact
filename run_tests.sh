#!/usr/bin/env bash

set -e

mkdir -p ./build
rm -r ./build

find ./tests -name '*.vt' |
    sort |
    python3 ./test-suite.py
