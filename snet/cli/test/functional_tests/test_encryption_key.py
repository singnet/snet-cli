import unittest
from func_tests import BaseTest, execute, PRIVATE_KEY
import unittest.mock as mock
from snet.cli.commands.commands import BlockchainCommand


class TestEncryptionKey(BaseTest):
    def setUp(self):
        super().setUp()
        self.key = PRIVATE_KEY
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
