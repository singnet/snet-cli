import warnings
import argcomplete
import unittest
import os

with warnings.catch_warnings():
    # Suppress the eth-typing package`s warnings related to some new networks
    warnings.filterwarnings("ignore", "Network .* does not have a valid ChainId. eth-typing should be "
                                      "updated with the latest networks.", UserWarning)
    from snet.cli import arguments

from snet.cli.config import Config

INFURA_KEY = os.environ.get("SNET_TEST_INFURA_KEY")
PRIVATE_KEY = os.environ.get("SNET_TEST_WALLET_PRIVATE_KEY")
ADDR = os.environ.get("SNET_TEST_WALLET_ADDRESS")
INFURA = f"https://sepolia.infura.io/v3/{INFURA_KEY}"
IDENTITY = "sepolia"


class StringOutput:
    def __init__(self):
        self.text = ""

    def write(self, text):
        self.text += text


def execute(args_list, parser, conf):
    try:
        argv = args_list
        try:
            args = parser.parse_args(argv)
        except TypeError:
            args = parser.parse_args(argv + ["-h"])
        f = StringOutput()
        getattr(args.cmd(conf, args, out_f=f), args.fn)()
        return f.text
    except Exception as e:
        raise


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.conf = Config()
        self.parser = arguments.get_root_parser(self.conf)
        argcomplete.autocomplete(self.parser)


if __name__ == "__main__":
    unittest.main()
