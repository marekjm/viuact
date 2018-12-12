#!/usr/bin/env python3

import sys


import frontend
import driver


def main(executable_name, args):
    driver.compile_file(**frontend.cc(executable_name, args))

main(sys.argv[0], sys.argv[1:])
