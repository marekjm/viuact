import env


def verbose(s):
    if env.VIUAC_VERBOSE:
        print(s)

def debug(s):
    if env.VIUAC_DEBUGGING:
        print(s)

def info(s):
    if env.VIUAC_INFO:
        print(s)
