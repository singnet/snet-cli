from func_tests import BaseTest, execute, ADDR
import unittest
import re


class TestChannels(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id = "SNet"
        self.org_2_id = "singularitynet"
        self.amount = "0.001"
        self.password = "12345"
        self.group = "default_group"
        data = execute(["channel", "print-filter-sender"], self.parser, self.conf)
        lines = data.split("\n")
        self.max_id = ""
        for line in lines:
            parts = line.split()
            if len(parts) >= 6 and parts[0].isdigit() and parts[-1].isdigit():
                self.max_id = parts[0]

    def test_channel_1_extend(self):
        execute(["account", "deposit", self.amount, "-y", "-q"], self.parser, self.conf)
        if self.max_id:
            result1 = execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
        else:
            block_number = int(execute(["channel", "block-number"], self.parser, self.conf))
            channel_open_output = execute(["channel", "open", self.org_id, self.group, self.amount, f"{block_number+10000}", "-y", "--open-new-anyway"], self.parser, self.conf)
            match = re.search(r"#channel_id\s+(\d+)", channel_open_output)
            self.max_id = match.group(1)
            execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
            result1 = execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser,
                              self.conf)
        # result2 = execute(["channel", "extend-add-for-org", self.org_id, "default_group", "--channel-id", f"{self.max_id}", "-y"], self.parser, self.conf)
        print(result1)
        assert "event: ChannelAddFunds" in result1

    def test_channel_2_print_filter_sender(self):
        result = execute(["channel", "print-filter-sender"], self.parser, self.conf)
        print(result)
        assert "Channels for sender: ", ADDR in result

    def test_channel_3_print_filter_group_sender(self):
        result = execute(["channel", "print-filter-group-sender", self.org_id, self.group], self.parser, self.conf)
        assert "Channels for sender: ", ADDR in result

    def test_channel_4_print_filter_group(self):
        result = execute(["channel", "print-filter-group", self.org_id, self.group], self.parser, self.conf)
        assert self.max_id in result

    def test_channel_5_print_filter_recipient(self):
        result = execute(["channel", "print-filter-recipient"], self.parser, self.conf)
        assert "Channels for recipient:", ADDR in result

    def test_channel_5_claim(self):
        execute(["account", "deposit", self.amount, "-y", "-q"], self.parser, self.conf)
        if self.max_id:
            execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
            result1 = execute(["channel", "claim-timeout", f"{self.max_id}", "-y"], self.parser, self.conf)
            execute(["account", "deposit", self.amount, "-y", "-q"], self.parser, self.conf)
            execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
            result2 = execute(["channel", "claim-timeout-all", "-y"], self.parser, self.conf)
        else:
            block_number = int(execute(["channel", "block-number"], self.parser, self.conf))
            execute(["channel", "open", self.org_id, self.group, self.amount, f"{block_number-1}", "-y"], self.parser, self.conf)
            execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
            result1 = execute(["channel", "claim-timeout", f"{self.max_id}", "-y"], self.parser, self.conf)
            execute(["account", "deposit", self.amount, "-y", "-q"], self.parser, self.conf)
            execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
            result2 = execute(["channel", "claim-timeout-all", "-y"], self.parser, self.conf)
        print(result1)
        assert ("event: ChannelSenderClaim" in result1) and ("event: ChannelSenderClaim" in result2)

    def test_channel_6_print_all(self):
        result = execute(["channel", "print-all", "-ds"], self.parser, self.conf)
        assert self.max_id in result

if __name__ == "__main__":
    unittest.main()
