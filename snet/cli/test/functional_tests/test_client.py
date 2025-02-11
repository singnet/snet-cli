from func_tests import BaseTest, execute, ADDR, PRIVATE_KEY, INFURA
import os
import unittest


class TestClient(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id = "egor-sing-test"
        self.service_id = "hate-detection"
        self.group = "default_group"
        self.identity_name = "some__name"
        self.method = "runsync"
        self.params = "./detection.json"
        self.endpoint = "https://ai-ui-service.singularitynet.io:8001"
        self.max_id = "357"
        self.nonce = "1"
        self.amount_in_cogs = "1"

    def test_0_preparations(self):
        identity_list=execute(["identity", "list"], self.parser, self.conf)
        if self.identity_name not in identity_list:
            execute(["identity", "create", self.identity_name, "key", "--private-key", PRIVATE_KEY, "-de"], self.parser, self.conf)
        execute(["network", "sepolia"], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert "network: sepolia" in result

    def test_1_channel_open(self):
        execute(["set", "default_eth_rpc_endpoint", INFURA], self.parser, self.conf)
        execute(["account", "deposit", "0.1", "-y"], self.parser, self.conf)
        self.block=int(execute(["channel", "block-number"], self.parser, self.conf))
        print(self.block)
        result = execute(["channel", "print-filter-group-sender", self.org_id, self.group], self.parser, self.conf)
        if ADDR not in result[13:]:
            result=execute(["channel", "open", self.org_id, "default_group", "0.0001", f"{self.block+100}", "-y"], self.parser, self.conf)
        else:
            pass
        print(result)
        assert "#channel_id" in result

    def test_2_service_call(self):
        params_file = open("detection.json", "w+")
        params_file.write("""{
    "input": {
        "text": "Hello man answer me soon"
    }
}
        """)
        params_file.close()
        result=execute(["client", "call", self.org_id, self.service_id, self.group, self.method, self.params, "-y"], self.parser, self.conf)
        assert "spam" in result

    def test_3_service_get_channel_state(self):
        result=execute(["client", "get-channel-state", self.max_id, self.endpoint], self.parser, self.conf)
        assert "current_unspent_amount_in_cogs = " in result

    def test_4_call_low_level(self):
        result = execute(["client", "call-lowlevel", self.org_id, self.service_id, self.group, self.max_id, self.nonce, self.amount_in_cogs, self.method, self.params], self.parser, self.conf)
        assert "spam" in result

    def test_5_get_api_registry(self):
        execute(["service", "get-api-registry", self.org_id, self.service_id, "./"], self.parser, self.conf)
        assert os.path.exists("./hate.proto")


if __name__ == "__main__":
    unittest.main()
