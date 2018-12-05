import sys

from snet_cli import arguments
from snet_cli.config import Config

__version__ = "0.1.8"


def main():
    argv = sys.argv[1:]
    conf   = Config()
    parser = arguments.get_root_parser(conf)

    try:
        args = parser.parse_args(argv)
    except TypeError:
        args = parser.parse_args(argv + ["-h"])

    try:
        getattr(args.cmd(conf, args), args.fn)()
    except Exception as e:
        if (args.print_traceback):
            raise
        else:
            print("Error:", e)
            print("If you want to see full Traceback then run:")
            print("snet --print-traceback [parameters]")
            sys.exit(42)
