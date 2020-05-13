#!/usr/bin/env bash

set -e

HELP_EXECUTABLE="$0"
HELP_EXEC_SPACE=$(echo "$0" | sed 's/./ /g')

HELP="EX/_NEW.SH(1)

NAME
    $HELP_EXECUTABLE - create new Viuact example

SYNOPSIS
    $HELP_EXECUTABLE <example-name>
    $HELP_EXEC_SPACE --help

DESCRIPTION
    Create  files for new  Viuact  example. If the  name is  given as  'foo' the
    script will emit two files in the ./ex directory:

      - ./ex/foo.sh
      - ./ex/foo.vt

    The ./ex/foo.sh file can be used to compile and run the program whose source
    code is contained by ./ex/foo.vt file.

AUTHOR
    Written by Marek Marecki.

COPYRIGHT
    Copyright © 2020 Marek Marecki

    This is Free Software published under GNU GPL version 3.

"


NAME=$1

if [[ $NAME == '' ]]; then
    1>&2 echo "error: $0 <example-name>"
    1>&2 echo "note: example: $0 foo"
    1>&2 echo "               will emit ./ex/foo.sh and ./ex/foo.lisp"
    1>&2 echo "note: use $0 --help for more information"
    exit 1
fi
if [[ $NAME == '--help' ]]; then
    echo -n "$HELP"
    exit 0
fi

if [[ -f ./ex/$NAME.sh ]]; then
    1>&2 echo "error: example named '$NAME' already exists"
    exit 1
fi

cp -v ./ex/_template.sh ./ex/$NAME.sh
sed -i "s/\\<_template\\>/$NAME/g" ./ex/$NAME.sh

cp -v ./ex/_template.vt ./ex/$NAME.vt
