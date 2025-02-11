from func_tests import BaseTest, execute, ADDR
import unittest

class TestContract(BaseTest):
    def setUp(self):
        super().setUp()
        self.last_channel_id = int(execute(["contract", "MultiPartyEscrow", "nextChannelId"], self.parser, self.conf)) - 1
        self.amount = "1"
        self.block_number = int(execute(["channel", "block-number"], self.parser, self.conf))
        self.channel = execute(["channel", "print-filter-sender"], self.parser, self.conf).split()[11]

    def test_SingularityNetToken_name(self):
        result = execute(["contract", "SingularityNetToken", "name"], self.parser, self.conf)
        assert "SingularityNet Token" in result

    def test_SingularityNetToken_decimals(self):
        result = execute(["contract", "SingularityNetToken", "decimals"], self.parser, self.conf)
        assert "8" in result

    def test_SingularityNetToken_symbol(self):
        result = execute(["contract", "SingularityNetToken", "symbol"], self.parser, self.conf)
        assert "AGIX" in result

    def test_SingularityNetToken_totalSupply(self):
        result = int(execute(["contract", "SingularityNetToken", "totalSupply"], self.parser, self.conf))
        assert 1772090920768158 <= result

    def test_SingularityNetToken_paused(self):
        result=execute(["contract", "SingularityNetToken", "paused"], self.parser, self.conf)
        assert "False" in result

    def test_MultiPartyEscrow_1_balances(self):
        result = int(execute(["contract", "MultiPartyEscrow", "balances", ADDR], self.parser, self.conf))
        assert result > 0

    def test_MultiPartyEscrow_token(self):
        result = execute(["contract", "MultiPartyEscrow", "token"], self.parser, self.conf)
        assert "0xf703b9aB8931B6590CFc95183be4fEf278732016" in result

    def test_MultiPartyEscrow_channels(self):
        result = execute(["contract", "MultiPartyEscrow", "channels", f"{self.last_channel_id}"], self.parser, self.conf)
        assert len(result) > 150

    def test_MultiPartyEscrow_addFunds(self):
        print(self.channel)
        result = execute(["contract", "MultiPartyEscrow", "channelAddFunds", self.channel, self.amount, "-y"], self.parser, self.conf)
        assert "event: ChannelAddFunds" in result

    def test_MultiPartyEscrow_channelExtend(self):
        result = execute(["contract", "MultiPartyEscrow", "channelExtend", self.channel, f"{self.block_number+100}", "-y"], self.parser, self.conf).split()[11]
        assert "event: ChannelExtend" in result

    def test_Registry_getOrganizationById(self):
        result = execute(["contract", "Registry", "getOrganizationById", "SNet"], self.parser, self.conf)
        assert len(result) > 400

    def test_Registry_listOrganizations(self):
        result = execute(["contract", "Registry", "listOrganizations"], self.parser, self.conf)
        assert len(result) > 12000

    def test_Registry_getServiceRegistrationById(self):
        result = execute(["contract", "Registry", "getServiceRegistrationById", "SNet", "example-service-constructor"], self.parser, self.conf)
        assert "True" in result

    def test_Registry_listServicesForOrganization(self):
        result = execute(["contract", "Registry", "listServicesForOrganization", "SNet"], self.parser, self.conf)
        assert "True" in result


if __name__ == "__main__":
    unittest.main()
