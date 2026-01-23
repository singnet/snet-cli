from func_tests import BaseTest, execute
import unittest


class Unset(BaseTest):
    def test_unset_filecoin(self):
        execute(["set", "filecoin_api_key", "1"], self.parser, self.conf)
        result = execute(["unset", "filecoin_api_key"], self.parser, self.conf)
        assert "unset" in result

    def test_unset_current_registry_at(self):
        execute(["set", "current_registry_at", "1"], self.parser, self.conf)
        result = execute(["unset", "current_registry_at"], self.parser, self.conf)
        assert "unset" in result

    def test_unset_current_multipartyescrow_at(self):
        execute(["set", "current_multipartyescrow_at", "1"], self.parser, self.conf)
        result = execute(["unset", "current_multipartyescrow_at"], self.parser, self.conf)
        assert "unset" in result

    def test_unset_current_singularitynettoken_at(self):
        execute(["set", "current_singularitynettoken_at", "1"], self.parser, self.conf)
        result = execute(["unset", "current_singularitynettoken_at"], self.parser, self.conf)
        assert "unset" in result


if __name__ == "__main__":
    unittest.main()
