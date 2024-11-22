import warnings
import argcomplete
import unittest
import unittest.mock as mock
import shutil
import os

from snet.cli.commands.commands import BlockchainCommand

with warnings.catch_warnings():
    # Suppress the eth-typing package`s warnings related to some new networks
    warnings.filterwarnings("ignore", "Network .* does not have a valid ChainId. eth-typing should be "
                                      "updated with the latest networks.", UserWarning)
    from snet.cli import arguments

from snet.cli.config import Config


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
        getattr(args.cmd(conf, args, out_f = f), args.fn)()
        return f.text
    except Exception as e:
        raise

class BaseTest(unittest.TestCase):
    def setUp(self):
        self.conf = Config()
        self.parser = arguments.get_root_parser(self.conf)
        argcomplete.autocomplete(self.parser)


class TestCommands(BaseTest):
    def test_balance_output(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        assert len(result.split("\n")) >= 4

    def test_balance_address(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        assert result.split("\n")[0].split()[1] == "0xe5D1fA424DE4689F9d2687353b75D7a8987900fD"

class TestDepositWithdraw(BaseTest):
    def setUp(self):
        super().setUp()
        self.balance_1: int
        self.balance_2: int
        self.amount = 0.1

    def test_deposit(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_1 = float(result.split("\n")[3].split()[1])
        execute(["account", "deposit", f"{self.amount}", "-y", "-q"], self.parser, self.conf)
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_2 = float(result.split("\n")[3].split()[1])
        assert self.balance_2 == self.balance_1 + self.amount

    def test_withdraw(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_1 = float(result.split("\n")[3].split()[1])
        execute(["account", "withdraw", f"{self.amount}", "-y", "-q"], self.parser, self.conf)
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_2 = float(result.split("\n")[3].split()[1])
        assert self.balance_2 == self.balance_1 - self.amount


class TestGenerateLibrary(BaseTest):
    def setUp(self):
        super().setUp()
        self.path = './temp_files'
        self.org_id = '26072b8b6a0e448180f8c0e702ab6d2f'
        self.service_id = 'Exampleservice'

    def test_generate(self):
        execute(["sdk", "generate-client-library", self.org_id, self.service_id, self.path], self.parser, self.conf)
        assert os.path.exists(f'{self.path}/{self.org_id}/{self.service_id}/python/')

    def tearDown(self):
        shutil.rmtree(self.path)


class TestEncryptionKey(BaseTest):
    def setUp(self):
        super().setUp()
        self.key = "1234567890123456789012345678901234567890123456789012345678901234"
        self.password = "some_pass"
        self.name = "some_name"
        self.default_name = "default_name"
        result = execute(["identity", "list"], self.parser, self.conf)
        if self.default_name not in result:
            execute(["identity", "create", self.default_name, "key", "--private-key", self.key, "-de"],
                             self.parser,
                             self.conf)

    def test_1_create_identity_with_encryption_key(self):
        with mock.patch('getpass.getpass', return_value=self.password):
            execute(["identity", "create", self.name, "key", "--private-key", self.key],
                             self.parser,
                             self.conf)
            result = execute(["identity", "list"], self.parser, self.conf)
            assert self.name in result

    def test_2_get_encryption_key(self):
        with mock.patch('getpass.getpass', return_value=self.password):
            execute(["identity", self.name], self.parser, self.conf)
            cmd = BlockchainCommand(self.conf, self.parser.parse_args(['session']))
            enc_key = cmd.config.get_session_field("private_key")
            res_key = cmd._get_decrypted_secret(enc_key)
            assert res_key == self.key

    def test_3_delete_identity(self):
        with mock.patch('getpass.getpass', return_value=self.password):
            execute(["identity", self.default_name], self.parser, self.conf)
            execute(["identity", "delete", self.name], self.parser, self.conf)
            result = execute(["identity", "list"], self.parser, self.conf)
            assert self.name not in result


if __name__ == "__main__":
    unittest.main()
