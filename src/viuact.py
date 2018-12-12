#!/usr/bin/env python3

import sys


import frontend
import driver


def main(executable_name, args):
    output_file_name = driver.compile_file(**frontend.cc(executable_name, args))
    driver.assemble_and_link(**frontend.opt([output_file_name]))

main(sys.argv[0], sys.argv[1:])
