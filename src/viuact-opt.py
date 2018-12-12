#!/usr/bin/env python3

import sys


import frontend
import driver


def main(args):
    driver.assemble_and_link(**frontend.opt(args))


main(sys.argv[1:])
