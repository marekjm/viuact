import sys


from viuact import env


def verbose(s):
    if env.VIUAC_VERBOSE:
        print(s)

def debug(s):
    if env.VIUAC_DEBUGGING:
        print(s)

def warn(s):
    sys.stderr.write('{}\n'.format(s))

def info(s):
    if env.VIUAC_INFO:
        print(s)
