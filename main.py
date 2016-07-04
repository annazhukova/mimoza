# !/usr/bin/env python
# encoding: utf-8

import getopt
import sys

from sbml_vis.mimoza_pipeline import process_sbml

__author__ = 'anna'
help_message = '''
Generalizes and visualizes an SBML model.
usage: main.py --model model.xml --verbose
'''


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def process_args(argv):
    try:
        opts, args = getopt.getopt(argv[1:], "m:h:v",
                                   ["help", "model=", "verbose"])
    except getopt.error, msg:
        raise Usage(msg)
    sbml, verbose = None, False
    # option processing
    for option, value in opts:
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ("-m", "--model"):
            sbml = value
        if option in ("-v", "--verbose"):
            verbose = True
    if not sbml:
        raise Usage(help_message)
    return sbml, verbose


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        sbml, verbose = process_args(argv)
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2
    process_sbml(sbml, verbose, ub_ch_ids=None, path=None, generalize=True, log_file=None)


if __name__ == "__main__":
    sys.exit(main())