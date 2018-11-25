import os

DEFAULT_OUTPUT_DIRECTORY = os.environ.get('VIUAC_OUTPUT_DIRECTORY', './build/_default')
VIUAC_LIBRARY_PATH = os.environ.get('VIUAC_LIBRARY_PATH', DEFAULT_OUTPUT_DIRECTORY).split(':')
