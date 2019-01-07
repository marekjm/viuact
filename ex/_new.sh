#!/usr/bin/env bash

set -e

NAME=$1

cp -v ./ex/_template.sh ./ex/$NAME.sh
sed -i "s/\\<_template\\>/$NAME/g" ./ex/$NAME.sh

cp -v ./ex/_template.lisp ./ex/$NAME.lisp
