#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import sys
import warnings

import argcomplete

with warnings.catch_warnings():
    # Suppress the eth-typing package`s warnings related to some new networks
    warnings.filterwarnings("ignore", "Network .* does not have a valid ChainId. eth-typing should be "
                                      "updated with the latest networks.", UserWarning)
    from snet.cli import arguments

from snet.cli.config import Config


def main():
    try:
        argv = sys.argv[1:]
        conf   = Config()
        parser = arguments.get_root_parser(conf)
        argcomplete.autocomplete(parser)

        try:
            args = parser.parse_args(argv)
        except TypeError:
            args = parser.parse_args(argv + ["-h"])

        getattr(args.cmd(conf, args), args.fn)()
    except Exception as e:
        if sys.argv[1] == "--print-traceback":
            raise
        else:
            print("Error:", e)
            print("If you want to see full Traceback then run:")
            print("snet --print-traceback [parameters]")
            sys.exit(42)
