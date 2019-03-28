#!/usr/bin/env python3

import sys


import viuact.frontend
import viuact.driver


def main(args):
    viuact.driver.assemble_and_link(**viuact.frontend.opt(args))


main(sys.argv[1:])
