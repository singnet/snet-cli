import unittest
from func_tests import BaseTest, execute, ADDR
import importlib


class TestCommands(BaseTest):
    def setUp(self):
        super().setUp()

    def test_balance_output(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        assert len(result.split("\n")) >= 4

    def test_balance_address(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        assert result.split("\n")[0].split()[1] == ADDR

    def test_version(self):
        file_path = "./version.py"
        spec = importlib.util.spec_from_file_location("version", file_path)
        version_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(version_module)
        self.version = version_module.__version__
        result = execute(["version"], self.parser, self.conf)
        assert f"version: {self.version}" in result


if __name__ == "__main__":
    unittest.main()
