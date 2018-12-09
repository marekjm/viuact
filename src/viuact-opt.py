#!/usr/bin/env python3

import sys
import os


VIUA_ASM_PATH = os.environ.get('VIUA_ASM_PATH', '../core/viuavm/build/bin/vm/asm')


def main(args):
    os.system('{} {}'.format(VIUA_ASM_PATH, args[0]))

main(sys.argv[1:])
