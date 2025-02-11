import unittest
from func_tests import BaseTest, execute, ADDR, IDENTITY, PRIVATE_KEY, INFURA, INFURA_KEY


class TestAAMainPreparations(BaseTest):
    def setUp(self):
        super().setUp()
        self.new_network = "auto_test"

    def test_1_identity_create(self):
        execute(["identity", "create", IDENTITY, "key", "--private-key", PRIVATE_KEY, "-de"], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert f"identity: {IDENTITY}" in result

    def test_2_set_network_mainnet(self):
        execute(["network", "mainnet"], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert "network: mainnet" in result

    def test_3_set_network_sepolia(self):
        execute(["network", "sepolia"], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert "network: sepolia" in result

    def test_41_network_create(self):
        result = execute(["network", "create", self.new_network, INFURA], self.parser, self.conf)
        assert f"add network with name='{self.new_network}'" in result

    def test_42_network_create_confirmation(self):
        execute(["network", self.new_network], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        execute(["network", "sepolia"], self.parser, self.conf)
        assert "network: ", self.new_network in result

    def test_5_set_infura(self):
        execute(["set", "default_eth_rpc_endpoint", INFURA], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert INFURA_KEY in result

    def test_6_print_account(self):
        result = execute(["account", "print"], self.parser, self.conf)
        print(result)
        assert ADDR in result

if __name__ == "__main__":
    unittest.main()
