import sys

from snet_cli import arguments
from snet_cli.config import conf


def main():
    argv = sys.argv[1:]
    parser = arguments.get_root_parser(conf)

    try:
        args = parser.parse_args(argv)
    except TypeError:
        args = parser.parse_args(argv + ["-h"])

    getattr(args.cmd(conf, args), args.fn)()
