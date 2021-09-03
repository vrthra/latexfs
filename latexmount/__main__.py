import os
import os.path
from latexmount.fs import init_fs

def print_help():
    print('''\
python -m latexmount <latex file>''')


def main(args):
    if len(args) < 2:
        return print_help()
    if not os.path.exists(args[1]):
        print("<latex file> %s does not exist" % args[1])
        exit(-1)
    dir_path = args[1] + '_mount'
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    init_fs(args[1], dir_path)

import sys
main(sys.argv)
