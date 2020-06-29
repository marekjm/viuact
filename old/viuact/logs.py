import sys


from viuact import env


def verbose(s):
    if env.VIUACT_VERBOSE:
        print(s)

def debug(s):
    if env.VIUACT_DEBUGGING:
        print(s)

def warn(s):
    sys.stderr.write('{}\n'.format(s))

def info(s):
    if env.VIUACT_INFO:
        print(s)
