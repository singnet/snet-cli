import warnings
import argcomplete
import unittest
import unittest.mock as mock
import shutil
import os
import importlib.util

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
        getattr(args.cmd(conf, args, out_f=f), args.fn)()
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
        result = execute(["account", "print"], self.parser, self.conf)
        print(result)
        assert ADDR in result


class TestABCommands(BaseTest):
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


class TestACDepositWithdrawTransfer(BaseTest):
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
        assert round(self.balance_2, 3) == round(self.balance_1, 3) + self.amount

    def test_withdraw(self):
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_1 = float(result.split("\n")[3].split()[1])
        execute(["account", "withdraw", f"{self.amount}", "-y", "-q"], self.parser, self.conf)
        result = execute(["account", "balance"], self.parser, self.conf)
        self.balance_2 = float(result.split("\n")[3].split()[1])
        assert round(self.balance_2, 3) == round(self.balance_1, 3) - self.amount

    def test_transfer(self):
        result = execute(["account", "transfer", ADDR, f"{self.amount}", "-y"], self.parser, self.conf)
        assert "TransferFunds" in result


class TestADGenerateLibrary(BaseTest):
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


class TestAEEncryptionKey(BaseTest):
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


class TestAFOrgMetadata(BaseTest):
    def setUp(self):
        super().setUp()
        self.success_msg = "Organization metadata is valid and ready to publish."
        self.name = "test_org"
        self.org_id = "test_org_id"
        self.org_type = "individual"
        self.org_description = "--description"
        self.org_short_description = "--short-description"
        self.org_url = "--url"
        self.group_name = "default_group"
        self.endpoint = "https://node1.naint.tech:62400"

    def test_metadata_init(self):
        execute(["organization", "metadata-init", self.name, self.org_id, self.org_type], self.parser, self.conf)
        execute(["organization", "metadata-add-description", self.org_description, "DESCRIPTION", self.org_short_description, "SHORT_DESCRIPTION", self.org_url, "https://URL"],
                self.parser,
                self.conf)
        execute(["organization", "add-group", self.group_name, ADDR, self.endpoint], self.parser, self.conf)
        result = execute(["organization", "validate-metadata"], self.parser, self.conf)
        assert self.success_msg in result

    def tearDown(self):
        os.remove(f"./organization_metadata.json")


class TestAGChannels(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id = "SNet"
        self.amount = "0.001"
        self.password = "12345"
        self.group = "default_group"
        data = execute(["channel", "print-filter-group", self.org_id, "default_group"], self.parser, self.conf)
        max_id = None
        for line in data.splitlines()[2:]:
            parts = line.split()
            if len(parts) < 7:
                continue

            channel_id = int(parts[0].lstrip("#"))
            value = int(parts[6])

            if value > 0:
                if max_id is None or channel_id > max_id:
                    max_id = channel_id
            self.max_id = str(max_id) if max_id is not None else None

    def test_channel_1_extend(self):
        execute(["account", "deposit", self.amount, "-y", "-q"], self.parser, self.conf)
        result1 = execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
        result2 = execute(["channel", "extend-add-for-org", self.org_id, "default_group", "--channel-id", f"{self.max_id}", "-y"], self.parser, self.conf)
        print(result2)
        assert f"channelId: ", self.max_id in result1

    def test_channel_2_print_filter_sender(self):
        result = execute(["channel", "print-filter-sender"], self.parser, self.conf)
        print(result)
        assert "Channels for sender: ", ADDR in result

    def test_channel_3_print_filter_group_sender(self):
        result = execute(["channel", "print-filter-group-sender", self.org_id, self.group], self.parser, self.conf)
        assert "Channels for sender: ", ADDR in result

    def test_channel_3_print_filter_group(self):
        result = execute(["channel", "print-filter-group", self.org_id, self.group], self.parser, self.conf)
        assert self.max_id in result


    def test_channel_4_claim(self):
        execute(["account", "deposit", self.amount, "-y", "-q"], self.parser, self.conf)
        execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
        result1 = execute(["channel", "claim-timeout", f"{self.max_id}", "-y"], self.parser, self.conf)
        execute(["account", "deposit", self.amount, "-y", "-q"], self.parser, self.conf)
        execute(["channel", "extend-add", self.max_id, "--amount", self.amount, "-y"], self.parser, self.conf)
        result2 = execute(["channel", "claim-timeout-all", "-y"], self.parser, self.conf)
        assert ("event: ChannelSenderClaim" in result1) and ("event: ChannelSenderClaim" in result2)



class TestAHClient(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id="egor-sing-test"
        self.service_id="hate-detection"
        self.group="default_group"
        self.identity_name="some_name"
        self.method="detection"
        self.params=("./detection.json")

    def test_0_preparations(self):
        identity_list=execute(["identity", "list"], self.parser, self.conf)
        if self.identity_name not in identity_list:
            execute(["identity", "create", self.identity_name, "key", "--private-key", PRIVATE_KEY, "-de"], self.parser, self.conf)
        execute(["network", "sepolia"], self.parser, self.conf)
        result = execute(["session"], self.parser, self.conf)
        assert "network: sepolia" in result

    def test_1_channel_open(self):
        execute(["set", "default_eth_rpc_endpoint", INFURA], self.parser, self.conf)
        execute(["account", "deposit", "0.0001", "-y"], self.parser, self.conf)
        self.block=int(execute(["channel", "block-number"], self.parser, self.conf))
        print(self.block)
        result=execute(["channel", "open", self.org_id, "default_group", "0.0001", f"{self.block+100000}", "-y"], self.parser, self.conf)
        assert "#channel_id" in result

    def test_2_service_call(self):
        params_file = open("detection.json", "w+")
        params_file.write("""
{
    "text": "Hello man try to answer me soon"
}
        """)
        params_file.close()
        result=execute(["client", "call", self.org_id, self.service_id, self.group, self.method, self.params, "-y"], self.parser, self.conf)
        assert "spam" in result



class TestAIOrganization(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id = "singularitynet"
        self.correct_msg = f"List of {self.org_id}'s Services:"

    def test_list_of_services(self):
        result = execute(["organization", "list-services", self.org_id], self.parser, self.conf)
        assert self.correct_msg in result

    def test_org_info(self):
        result = execute(["organization", "info", self.org_id], self.parser, self.conf)
        assert "Organization Name" in result


class TestAJOnboardingOrgAndServ(BaseTest):
    def setUp(self):
        super().setUp()
        self.identity_name = "some_name"
        self.proto = "./"
        self.org_name = "auto_test"
        self.org_id = "auto_test"
        self.org_type = "individual"
        self.description = "DESCRIPTION"
        self.short_description = "SHORT DESCRIPTION"
        self.url = "https://URL.com"
        self.group_name = "default_group"
        self.endpoint = "https://node1.naint.tech:62400"
        self.password = "12345"
        self.service_id = "auto_test_service"
        self.new_description = "NEW DESCRIPTION"
        self.free_calls = "100"
        self.contributor = "Stasy"
        self.contributor_mail = "stasy@hotmail.com"
        self.tags = "new", "text2text", "t2t", "punctuality"

    def test_0_preparation(self):
        identity_list = execute(["identity", "list"], self.parser, self.conf)
        if self.identity_name not in identity_list:
            execute(["identity", "create", self.identity_name, "key", "--private-key", PRIVATE_KEY, "-de"], self.parser, self.conf)
        execute(["network", "sepolia"], self.parser, self.conf)
        proto_file = open("ExampleService.proto", "w+")
        proto_file.write("""syntax = "proto3";

package example_service;

message Numbers {
    float a = 1;
    float b = 2;
}

message Result {
    float value = 1;
}

service Calculator {
    rpc add(Numbers) returns (Result) {}
    rpc sub(Numbers) returns (Result) {}
    rpc mul(Numbers) returns (Result) {}
    rpc div(Numbers) returns (Result) {}
}""")
        proto_file.close()
        result = execute(["session"], self.parser, self.conf)
        assert "network: sepolia" in result

    def test_1_metadata_init(self):
        execute(["organization", "metadata-init", self.org_id, self.org_name, self.org_type], self.parser, self.conf)
        execute(["organization", "metadata-add-description", "--description", self.description, "--short-description", self.short_description, "--url", self.url],
                self.parser,
                self.conf)
        execute(["organization", "add-group", self.group_name, ADDR, self.endpoint], self.parser, self.conf)
        execute(["service", "metadata-init", self.proto, self.service_id], self.parser, self.conf)
        assert os.path.exists("./organization_metadata.json"), "File organization_metadata.json was not created!"

    def test_2_create_organization(self):
        result = execute(["organization", "create", self.org_id, "-y"], self.parser, self.conf)
        assert "event: OrganizationCreated" in result

    def test_3_create_service(self):
        result = execute(["service", "publish", self.org_id, self.service_id, "-y"], self.parser, self.conf)
        assert "event: ServiceCreated" in result

    def test_4_lists(self):
        result1 = execute(["organization", "list"], self.parser, self.conf)
        result2 = execute(["organization", "list-org-names"], self.parser, self.conf)
        result3 = execute(["organization", "list-my"], self.parser, self.conf)
        result4 = execute(["organization", "list-services", self.org_id], self.parser, self.conf)
        assert (self.org_id in result1) and (self.org_name in result2) and (self.org_id in result3) and (self.service_id in result4)

    def test_5_change_members(self):
        result_add = execute(["organization", "add-members", self.org_id, ADDR, "-y"], self.parser, self.conf)
        result_rem = execute(["organization", "rem-members", self.org_id, ADDR, "-y"], self.parser, self.conf)
        # result_change_owner = execute(["organization", "change-owner", self.org_id, ADDR], self.parser, self.conf)
        assert "event: OrganizationModified" in result_rem

    def test_6_change_org_metadata(self):
        execute(["organization", "metadata-add-description", "--description", self.new_description], self.parser, self.conf)
        execute(["organization", "update-metadata", self.org_id, "-y"], self.parser, self.conf)
        result = execute(["organization", "print-metadata", self.org_id], self.parser, self.conf)
        assert self.new_description in result


    def test_7_change_service_metadata(self):
        execute(["service", "metadata-remove-group", self.group_name], self.parser, self.conf)
        execute(["service", "metadata-add-group", self.group_name], self.parser, self.conf)
        execute(["service", "metadata-set-free-calls", self.group_name, self.free_calls], self.parser, self.conf)
        execute(["service", "metadata-set-freecall-signer-address", self.group_name, ADDR], self.parser, self.conf)
        execute(["service", "metadata-add-description", "--description", self.new_description, "--short-description", self.short_description, "--url", self.url],
                self.parser,
                self.conf)
        execute(["service", "metadata-add-contributor", self.contributor, self.contributor_mail], self.parser, self.conf)
        execute(["service", "metadata-remove-contributor", self.contributor_mail], self.parser, self.conf)
        execute(["service", "metadata-add-contributor", self.contributor, self.contributor_mail], self.parser, self.conf)
        execute(["service", "metadata-add-tags", self.tags], self.parser, self.conf)
        execute(["service", "update-metadata", self.org_id, self.service_id, "-y"], self.parser, self.conf)
        result = execute(["service", "print-metadata", self.org_id, self.service_id], self.parser, self.conf)
        print(execute(["service", "print-metadata", self.org_id, self.service_id], self.parser, self.conf))
        print(execute(["service", "print-service-status", self.org_id, self.service_id], self.parser, self.conf))
        assert self.contributor in result


    def test_8_delete_service(self):
        result = execute(["service", "delete", self.org_id, self.service_id, "-y"], self.parser, self.conf)
        os.remove(f"./service_metadata.json")
        os.remove(f"./ExampleService.proto")
        assert "event: ServiceDeleted" in result

    def test_9_delete_organization(self):
        result=execute(["organization", "delete", self.org_id, "-y"], self.parser, self.conf)
        os.remove(f"./organization_metadata.json")
        assert "event: OrganizationDeleted" in result


if __name__ == "__main__":
    unittest.main()
