import unittest
from func_tests import BaseTest, execute, ADDR
import math


class TestDepositWithdrawTransfer(BaseTest):
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
        assert math.isclose(self.balance_2, self.balance_1 + self.amount, rel_tol=1e-3)

    def test_withdraw(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_1 = float(result.split("\n")[3].split()[1])
        execute(["account", "withdraw", f"{self.amount}", "-y", "-q"], self.parser, self.conf)
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_2 = float(result.split("\n")[3].split()[1])
        assert math.isclose(self.balance_2, self.balance_1 - self.amount, rel_tol=1e-3)

    def test_transfer(self):
        result = execute(["account", "transfer", ADDR, f"{self.amount}", "-y"], self.parser, self.conf)
        assert "TransferFunds" in result


if __name__ == "__main__":
    unittest.main()
