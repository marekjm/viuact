#!/usr/bin/env python3

import sys


import viuact.frontend
import viuact.driver


def main(executable_name, args):
    viuact.driver.compile_file(**viuact.frontend.cc(executable_name, args))

main(sys.argv[0], sys.argv[1:])
