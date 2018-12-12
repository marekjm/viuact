#!/usr/bin/env python3

import sys


import driver


def main(args):
    main_source_file = args[0]
    main_output_file = (args[1] if len(args) >= 2 else 'a.out')
    driver.assemble_and_link(main_source_file, main_output_file)


main(sys.argv[1:])
