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
        getattr(args.cmd(conf, args, out_f = f), args.fn)()
        return f.text
    except Exception as e:
        raise


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.conf = Config()
        self.parser = arguments.get_root_parser(self.conf)
        argcomplete.autocomplete(self.parser)


class TestAAMainPreparations(BaseTest):
    def setUp(self):
        super().setUp()

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

    def test_4_set_infura(self):
        execute(["set", "default_eth_rpc_endpoint", INFURA], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert INFURA_KEY in result

    def test_5_print_account(self):
        result=execute(["account", "print"], self.parser, self.conf)
        assert ADDR in result

class TestCommands(BaseTest):
    def setUp(self):
        super().setUp()
        self.version='2.3.0'
    def test_balance_output(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        assert len(result.split("\n")) >= 4

    def test_balance_address(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        assert result.split("\n")[0].split()[1] == ADDR

    def test_version(self):
        result = execute(["version"], self.parser, self.conf)
        assert f"version: {self.version}" in result

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


class TestOrgMetadata(BaseTest):
    def setUp(self):
        super().setUp()
        self.success_msg = "OK. Ready to publish."
        self.name = "test_org"
        self.org_id = "test_org_id"
        self.org_type = "individual"

    def test_metadata_init(self):
        execute(["organization", "metadata-init", self.name, self.org_id, self.org_type], self.parser, self.conf)
        result = execute(["organization", "validate-metadata"], self.parser, self.conf)
        assert self.success_msg in result

    def tearDown(self):
        os.remove(f"./organization_metadata.json")


class TestChannels(BaseTest):
    def setUp(self):
        super().setUp()
        self.ID_flag="--only-id"
        self.ID="1"
        self.amount="1"
        self.password="12345"
    def test_channel_open(self):
        result=execute(["channel", "print-all", self.ID_flag], self.parser, self.conf)
        maximum_first = max(int(x) for x in result.split() if x.isdigit())
    def test_channel_extend(self):
        with mock.patch('getpass.getpass', return_value=self.password):
            result=execute(["channel", "extend-add", self.ID, "--amount", self.amount, "-y"], self.parser, self.conf)
            assert "channelId: ", self.ID in result


class TestClient(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id="26072b8b6a0e448180f8c0e702ab6d2f"
        self.service_id="Exampleservice"
        self.group="default_group"
        self.method="add"
        self.params=('{'
                     '"a": 10,'
                     '"b": 32'
                     '}')
    def test_service_call(self):
        result=execute(["client", "call", self.org_id, self.service_id, self.group, self.method, self.params], self.parser, self.conf)
        assert "42" in result

class TestOrganization(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id="singularitynet"
        self.correct_msg=f"List of {self.org_id}'s Services:"
    def test_list_of_services(self):
        result=execute(["organization", "list-services", self.org_id], self.parser, self.conf)
        assert self.correct_msg in result
    def test_org_info(self):
        result=execute(["organization", "info", self.org_id], self.parser, self.conf)
        assert "Organization Name" in result


class TestOnboardingOrg(BaseTest):
    def setUp(self):
        super().setUp()
        self.identity_name="some__name"
        self.org_name="auto_test"
        self.org_id="auto_test"
        self.org_type="individual"
        self.org_description="--description"
        self.org_short_description="--short-description"
        self.org_url="--url"
        self.group_name= "default_group"
        self.endpoint="https://node1.naint.tech:62400"
        self.password="12345"
    def test_0_preparation(self):
        identity_list=execute(["identity", "list"], self.parser, self.conf)
        if self.identity_name not in identity_list:
            execute(["identity", "create", self.identity_name, "key", "--private-key", PRIVATE_KEY, "-de"], self.parser, self.conf)
        execute(["network", "sepolia"], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert "network: sepolia" in result
    def test_1_metadata_init(self):
        execute(["organization", "metadata-init", self.org_id, self.org_name, self.org_type], self.parser, self.conf)
        execute(["organization", "metadata-add-description", self.org_description, "DESCRIPTION", self.org_short_description, "SHORT_DESCRIPTION", self.org_url, "URL"],
                self.parser,
                self.conf)
        execute(["organization", "add-group", self.group_name, ADDR, self.endpoint], self.parser, self.conf)
        assert os.path.exists("./organization_metadata.json"), "File organization_metadata.json was not created!"
    def test_2_create_organization(self):
        with mock.patch('getpass.getpass', return_value=self.password):
            result=execute(["organization", "create", self.org_id, "-y"], self.parser, self.conf)
            assert "event: OrganizationCreated" in result
    def test_3_delete_organization(self):
        with mock.patch('getpass.getpass', return_value=self.password):
            result=execute(["organization", "delete", self.org_id, "-y"], self.parser, self.conf)
            os.remove(f"./organization_metadata.json")
            assert "event: OrganizationDeleted" in result


if __name__ == "__main__":
    unittest.main()
