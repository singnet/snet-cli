import base64
import getpass
import json
import secrets
import sys
from pathlib import Path
from textwrap import indent

import ipfshttpclient
import jsonschema
from lighthouseweb3 import Lighthouse
import yaml
import web3
from cryptography.fernet import InvalidToken
from snet.contracts import get_contract_def

from snet.cli.contract import Contract
from snet.cli.identity import KeyIdentityProvider, KeyStoreIdentityProvider, LedgerIdentityProvider, \
    MnemonicIdentityProvider, RpcIdentityProvider, TrezorIdentityProvider, get_kws_for_identity_type
from snet.cli.metadata.organization import OrganizationMetadata, PaymentStorageClient, Payment, Group
from snet.cli.utils.config import get_contract_address, get_field_from_args_or_session, \
    read_default_contract_address, decrypt_secret
from snet.cli.utils.ipfs_utils import get_from_ipfs_and_checkhash, \
    hash_to_bytesuri, publish_file_in_ipfs, publish_file_in_filecoin
from snet.cli.utils.utils import DefaultAttributeObject, get_web3, is_valid_url, serializable, type_converter, \
    get_cli_version, bytes32_to_str, bytesuri_to_hash, get_file_from_filecoin


class Command(object):
    def __init__(self, config, args, out_f=sys.stdout, err_f=sys.stderr):
        self.config = config
        self.args = args
        self.out_f = out_f
        self.err_f = err_f

    def _error(self, message):
        self._printerr("ERROR: {}".format(message))
        sys.exit(1)

    def _ensure(self, condition, message):
        if not condition:
            self._error(message)

    @staticmethod
    def _print(message, fd):
        message = str(message) + "\n"
        try:
            fd.write(message)
        except UnicodeEncodeError:
            if hasattr(fd, "buffer"):
                fd.buffer.write(message.encode("utf-8"))
            else:
                raise

    def _printout(self, message):
        if self.out_f is not None:
            self._print(message, self.out_f)

    def _printerr(self, message):
        if self.err_f is not None:
            self._print(message, self.err_f)

    def _pprint(self, item):
        self._printout(indent(yaml.dump(json.loads(json.dumps(item, default=serializable)), default_flow_style=False,
                                        indent=4), "    "))

    def _pprint_receipt_and_events(self, receipt, events):
        if self.args.verbose:
            self._pprint({"receipt": receipt, "events": events})
        elif self.args.quiet:
            self._pprint({"transactionHash": receipt["transactionHash"]})
        else:
            self._pprint({"receipt_summary": {"blockHash": receipt["blockHash"],
                                              "blockNumber": receipt["blockNumber"],
                                              "cumulativeGasUsed": receipt["cumulativeGasUsed"],
                                              "gasUsed": receipt["gasUsed"],
                                              "transactionHash": receipt["transactionHash"]},
                          "event_summaries": [{"args": e["args"], "event": e["event"]} for e in events]})

    def _get_ipfs_client(self):
        ipfs_endpoint = self.config.get_ipfs_endpoint()
        return ipfshttpclient.connect(ipfs_endpoint)

    def _get_filecoin_client(self):
        lighthouse_token = self.config.get_filecoin_key()
        return Lighthouse(token=lighthouse_token)


class VersionCommand(Command):
    def show(self):
        self._pprint({"version": get_cli_version()})


"""
# Temporally deprecated

class CachedGasPriceStrategy:
    def __init__(self, gas_price_param):
        self.gas_price_param = gas_price_param
        self.cached_gas_price = None

    def __call__(self, w3, transaction_params):
        if self.cached_gas_price is None:
            self.cached_gas_price = int(
                self.calc_gas_price(w3, transaction_params))
        return self.cached_gas_price

    def calc_gas_price(self, w3, transaction_params):
        gas_price_param = self.gas_price_param
        if gas_price_param.isdigit():
            return int(self.gas_price_param)
        if gas_price_param == "fast":
            return fast_gas_price_strategy(w3, transaction_params)
        if gas_price_param == "medium":
            return medium_gas_price_strategy(w3, transaction_params)
        if gas_price_param == "slow":
            return slow_gas_price_strategy(w3, transaction_params)
        raise Exception("Unknown gas price strategy: %s" % gas_price_param)

    def is_going_to_calculate(self):
        return self.cached_gas_price is None and not self.gas_price_param.isdigit()
"""


class BlockchainCommand(Command):
    def __init__(self, config, args, out_f=sys.stdout, err_f=sys.stderr, w3=None, ident=None):
        super(BlockchainCommand, self).__init__(config, args, out_f, err_f)
        self.w3 = w3 or get_web3(self.get_eth_endpoint())
        self.ident = ident or self.get_identity()

    def get_eth_endpoint(self):
        # the only one source of eth_rpc_endpoint is the configuration file
        return self.config.get_session_field("default_eth_rpc_endpoint")

    def get_wallet_index(self):
        return int(get_field_from_args_or_session(self.config, self.args, "wallet_index"))

    def get_gas_price_param(self):
        return get_field_from_args_or_session(self.config, self.args, "gas_price")

    def get_gas_price_verbose(self):
        # gas price is not given explicitly in Wei
        self._printerr("# Calculating gas price... one moment..")
        gas_price = self.w3.eth.gas_price
        if gas_price <= 15000000000:
            gas_price += gas_price * 1 / 3
        elif gas_price > 15000000000 and gas_price <= 50000000000:
            gas_price += gas_price * 1 / 5
        elif gas_price > 50000000000 and gas_price <= 150000000000:
            gas_price += 7000000000
        elif gas_price > 150000000000:
            gas_price += gas_price * 1 / 10
        self._printerr("# gas_price = %f GWei" % (gas_price * 1E-9))
        return int(gas_price)

    def get_mpe_address(self):
        return get_contract_address(self, "MultiPartyEscrow")

    def get_registry_address(self):
        return get_contract_address(self, "Registry")

    def get_identity(self):
        identity_type = self.config.get_session_field("identity_type")

        if identity_type == "rpc":
            return RpcIdentityProvider(self.w3, self.get_wallet_index())
        if identity_type == "mnemonic":
            return MnemonicIdentityProvider(self.w3, self.config.get_session_field("mnemonic"), self.get_wallet_index())
        if identity_type == "trezor":
            return TrezorIdentityProvider(self.w3, self.get_wallet_index())
        if identity_type == "ledger":
            return LedgerIdentityProvider(self.w3, self.get_wallet_index())
        if identity_type == "key":
            return KeyIdentityProvider(self.w3, self.config.get_session_field("private_key"))
        if identity_type == "keystore":
            return KeyStoreIdentityProvider(self.w3, self.config.get_session_field("keystore_path"))

    def check_ident(self):
        identity_type = self.config.get_session_field("identity_type")
        if get_kws_for_identity_type(identity_type)[0][1] and not self.ident.private_key:
            if identity_type == "key":
                secret = self.config.get_session_field("private_key")
            else:
                secret = self.config.get_session_field("mnemonic")
            decrypted_secret = self._get_decrypted_secret(secret)
            self.ident.set_secret(decrypted_secret)

    def _get_decrypted_secret(self, secret):
        decrypted_secret = None
        try:
            password = getpass.getpass("Password: ")
            decrypted_secret = decrypt_secret(secret, password)
        except InvalidToken:
            self._printout("Wrong password! Try again")
        if not decrypted_secret:
            try:
                password = getpass.getpass("Password: ")
                decrypted_secret = decrypt_secret(secret, password)
            except InvalidToken:
                self._printerr("Wrong password! Operation failed.")
                exit(1)
        return decrypted_secret

    def get_contract_argser(self, contract_address, contract_function, contract_def, **kwargs):
        def f(*positional_inputs, **named_inputs):
            args_dict = self.args.__dict__.copy()
            args_dict.update(dict(
                at=contract_address,
                contract_function=contract_function,
                contract_def=contract_def,
                contract_positional_inputs=positional_inputs,
                **kwargs
            ))
            for k, v in named_inputs.items():
                args_dict["contract_named_input_{}".format(k)] = v
            return DefaultAttributeObject(**args_dict)

        return f

    def get_contract_command(self, contract_name, contract_address, contract_fn, contract_params, is_silent=True):
        contract_def = get_contract_def(contract_name)
        if is_silent:
            out_f = None
            err_f = None
        else:
            out_f = self.out_f
            err_f = self.err_f
        return ContractCommand(config=self.config,
                               args=self.get_contract_argser(
                                   contract_address=contract_address,
                                   contract_function=contract_fn,
                                   contract_def=contract_def,
                                   contract_name=contract_name)(*contract_params),
                               out_f=out_f,
                               err_f=err_f,
                               w3=self.w3,
                               ident=self.ident)

    def call_contract_command(self, contract_name, contract_fn, contract_params, is_silent=True):
        contract_address = get_contract_address(self, contract_name)
        return self.get_contract_command(contract_name, contract_address,
                                         contract_fn, contract_params, is_silent).call()

    def transact_contract_command(self, contract_name, contract_fn, contract_params, is_silent=False):
        contract_address = get_contract_address(self, contract_name)
        return self.get_contract_command(contract_name, contract_address, contract_fn, contract_params,
                                         is_silent).transact()


class IdentityCommand(Command):
    def create(self):
        identity = {}

        identity_name = self.args.identity_name
        self._ensure(identity_name not in self.config.get_all_identities_names(),
                     "identity_name {} already exists".format(identity_name))

        identity_type = self.args.identity_type
        identity["identity_type"] = identity_type

        for kw, is_secret in get_kws_for_identity_type(identity_type):
            value = getattr(self.args, kw)
            if value is None and is_secret:
                kw_prompt = "{}: ".format(" ".join(kw.capitalize().split("_")))
                value = getpass.getpass(kw_prompt) or None
            self._ensure(
                value is not None, "--{} is required for identity_type {}".format(kw, identity_type))
            identity[kw] = value

        if self.args.network:
            identity["network"] = self.args.network
        identity["default_wallet_index"] = self.args.wallet_index

        password = None
        if not self.args.do_not_encrypt and get_kws_for_identity_type(identity_type)[0][1]:
            self._printout("For 'mnemonic' and 'key' identity_type, secret encryption is enabled by default, "
                           "so you need to come up with a password that you then need to enter on every transaction. "
                           "To disable encryption, use the '-de' or '--do-not-encrypt' argument.")
            password = getpass.getpass("Password: ")
            self._ensure(password is not None, "Password cannot be empty")
            pwd_confirm = getpass.getpass("Confirm password: ")
            self._ensure(password == pwd_confirm, "Passwords do not match")

        self.config.add_identity(identity_name, identity, self.out_f, password)


    def list(self):
        for identity_section in filter(lambda x: x.startswith("identity."), self.config.sections()):
            identity = self.config[identity_section]
            key_is_secret_lookup = {}

            identity_type = self.config.get(identity_section, 'identity_type')
            for kw, is_secret in get_kws_for_identity_type(identity_type):
                key_is_secret_lookup[kw] = is_secret

            self._pprint({
                identity_section[len("identity."):]: {
                    k: (v if not key_is_secret_lookup.get(k, False) else "xxxxxx") for k, v in identity.items()
                }
            })

    def delete(self):
        self.config.delete_identity(self.args.identity_name)

    def set(self):
        self.config.set_session_identity(self.args.identity_name, self.out_f)


class NetworkCommand(Command):
    def list(self):
        for network_section in filter(lambda x: x.startswith("network."), self.config.sections()):
            network = self.config[network_section]
            self._pprint({network_section[len("network."):]: {
                k: v for k, v in network.items()}})

    def create(self):
        network_id = None
        w3 = get_web3(self.args.eth_rpc_endpoint)
        if not self.args.skip_check:
            # check endpoint by getting its network_id
            network_id = w3.net.version

        self._printout("add network with name='%s' with networkId='%s'" % (
            self.args.network_name, str(network_id)))

        default_gas_price = w3.eth.gas_price
        self.config.add_network(
            self.args.network_name, self.args.eth_rpc_endpoint, default_gas_price)

    def set(self):
        self.config.set_session_network(self.args.network_name, self.out_f)


class SessionSetCommand(Command):
    def set(self):
        self.config.set_session_field(
            self.args.key, self.args.value, self.out_f)

    def unset(self):
        self.config.unset_session_field(self.args.key, self.out_f)


class SessionShowCommand(BlockchainCommand):

    def show(self):
        rez = self.config.session_to_dict()
        key = "network.%s" % rez['session']['network']
        self.populate_contract_address(rez, key)
        # we don't want to who private_key and mnemonic
        for d in rez.values():
            d.pop("private_key", None)
            d.pop("mnemonic", None)
        self._pprint(rez)

    def populate_contract_address(self, rez, key):
        try:
            rez[key]['default_registry_at'] = read_default_contract_address(
                w3=self.w3, contract_name="Registry")
            rez[key]['default_multipartyescrow_at'] = read_default_contract_address(
                w3=self.w3, contract_name="MultiPartyEscrow")
            rez[key]['default_singularitynettoken_at'] = read_default_contract_address(
                w3=self.w3, contract_name="SingularityNetToken")
        except Exception as e:
            pass
        return


class ContractCommand(BlockchainCommand):
    def call(self):
        contract_address = get_contract_address(self, self.args.contract_name,
                                                "--at is required to specify target contract address")

        abi = self.args.contract_def["abi"]

        contract = Contract(self.w3, contract_address, abi)

        positional_inputs = getattr(
            self.args, "contract_positional_inputs", [])
        named_inputs = {
            name[len("contract_named_input_"):]: value for name, value
            in self.args.__dict__.items() if name.startswith("contract_named_input_")
        }

        result = contract.call(self.args.contract_function,
                               *positional_inputs, **named_inputs)
        self._printout(result)
        return result

    def transact(self):
        self.check_ident()
        contract_address = get_contract_address(self, self.args.contract_name,
                                                "--at is required to specify target contract address")

        abi = self.args.contract_def["abi"]

        contract = Contract(self.w3, contract_address, abi)

        positional_inputs = getattr(
            self.args, "contract_positional_inputs", [])
        named_inputs = {
            name[len("contract_named_input_"):]: value for name, value
            in self.args.__dict__.items() if name.startswith("contract_named_input_")
        }

        gas_price = self.get_gas_price_verbose()

        txn = contract.build_transaction(self.args.contract_function,
                                         self.ident.get_address(),
                                         gas_price,
                                         *positional_inputs,
                                         **named_inputs)

        if not self.args.yes or self.args.verbose:
            self._pprint({"transaction": txn})

        proceed = self.args.yes or input("Proceed? (y/n): ") == "y"

        if proceed:
            receipt = self.ident.transact(txn, self.err_f)
            events = contract.process_receipt(receipt)
            self._pprint_receipt_and_events(receipt, events)
            return receipt, events
        else:
            self._error("Cancelled")


class OrganizationCommand(BlockchainCommand):

    def add_group(self):
        metadata_file = self.args.metadata_file

        try:
            with open(metadata_file, 'r') as f:
                org_metadata = OrganizationMetadata.from_json(json.load(f))
        except Exception as e:
            print(
                "Organization metadata json file not found ,Please check --metadata-file path ")
            raise e

        for endpoint in self.args.endpoints:
            if not is_valid_url(endpoint):
                raise Exception(f"Invalid {endpoint} endpoint passed")

        payment_storage_client = PaymentStorageClient(self.args.payment_channel_connection_timeout,
                                                      self.args.payment_channel_request_timeout,
                                                      self.args.endpoints)
        payment = Payment(self.args.payment_address, self.args.payment_expiration_threshold,
                          self.args.payment_channel_storage_type, payment_storage_client)
        group_id = base64.b64encode(secrets.token_bytes(32))

        group = Group(self.args.group_name, group_id.decode("ascii"), payment)
        org_metadata.add_group(group)
        org_metadata.save_pretty(metadata_file)

    def remove_group(self):
        group_id = self.args.group_id
        metadata_file = self.args.metadata_file

        try:
            with open(metadata_file, 'r') as f:
                org_metadata = OrganizationMetadata.from_json(json.load(f))
        except Exception as e:
            print(
                "Organization metadata json file not found ,Please check --metadata-file path ")
            raise e

        existing_groups = org_metadata.groups
        updated_groups = [group for group in existing_groups if not group_id == group.group_id]
        org_metadata.groups = updated_groups
        org_metadata.save_pretty(metadata_file)

    def set_changed_values_for_group(self, group):
        # if value of a parameter is None that means it was not updated

        if self.args.endpoints:
            group.update_endpoints(self.args.endpoints)
        if self.args.payment_address:
            group.update_payment_address(self.args.payment_address)
        if self.args.payment_expiration_threshold:
            group.update_payment_expiration_threshold(self.args.payment_expiration_threshold)
        if self.args.payment_channel_storage_type:
            group.update_payment_channel_storage_type(self.args.payment_channel_storage_type)
        if self.args.payment_channel_connection_timeout:
            group.update_connection_timeout(self.args.payment_channel_connection_timeout)
        if self.args.payment_channel_request_timeout:
            group.update_request_timeout(self.args.payment_channel_request_timeout)

    def update_group(self):
        group_id = self.args.group_id
        metadata_file = self.args.metadata_file
        try:
            with open(metadata_file, 'r') as f:
                org_metadata = OrganizationMetadata.from_json(json.load(f))
        except Exception as e:
            print(
                "Organization metadata json file not found ,Please check --metadata-file path ")
            raise e
        existing_groups = org_metadata.groups
        for group in existing_groups:
            if group_id == group.group_id:
                self.set_changed_values_for_group(group)

        org_metadata.save_pretty(metadata_file)

    def initialize_metadata(self):
        org_id = self.args.org_id
        metadata_file_name = self.args.metadata_file

        # Check if Organization already exists
        found = self._get_organization_by_id(org_id)[0]
        if found:
            raise Exception(
                "\nOrganization with id={} already exists!\n".format(org_id))
        org_metadata = OrganizationMetadata(self.args.org_name, org_id, self.args.org_type)
        org_metadata.save_pretty(metadata_file_name)

    def print_metadata(self):
        org_id = self.args.org_id
        org_metadata = self._get_organization_metadata_from_registry(org_id, False)
        self._printout(org_metadata.get_json_pretty())

    def _get_organization_registration(self, org_id):
        params = [type_converter("bytes32")(org_id)]
        rez = self.call_contract_command(
            "Registry", "getOrganizationById", params)
        if not rez[0]:
            raise Exception("Cannot find  Organization with id=%s" % (
                self.args.org_id))
        return {"orgMetadataURI": rez[2]}

    def _get_organization_metadata_from_registry(self, org_id, check_url=True):
        rez = self._get_organization_registration(org_id)
        storage_type, metadata_hash = bytesuri_to_hash(rez["orgMetadataURI"])
        if storage_type == "ipfs":
            metadata = get_from_ipfs_and_checkhash(self._get_ipfs_client(), metadata_hash)
        else:
            metadata = get_file_from_filecoin(metadata_hash)
        metadata = metadata.decode("utf-8")
        return OrganizationMetadata.from_json(json.loads(metadata), check_url)

    def _get_organization_by_id(self, org_id):
        org_id_bytes32 = type_converter("bytes32")(org_id)
        if len(org_id_bytes32) > 32:
            raise Exception("Your org_id is too long, it should be 32 bytes or less. len(org_id_bytes32)=%i" % (
                len(org_id_bytes32)))
        return self.call_contract_command("Registry", "getOrganizationById", [org_id_bytes32])

    # TODO: It would be better to have standard nargs="+" in argparse for members.
    #      But we keep comma separated members for backward compatibility
    def get_members_from_args(self):
        if not self.args.members:
            return []
        members = [m.replace("[", "").replace("]", "")
                   for m in self.args.members.split(',')]
        for m in members:
            if not web3.Web3.is_checksum_address(m):
                raise Exception(
                    "Member account %s is not a valid Ethereum checksum address" % m)
        return members

    def list(self):
        org_list = self.call_contract_command(
            "Registry", "listOrganizations", [])

        self._printout("# OrgId")
        for idx, org_id in enumerate(org_list):
            self._printout(bytes32_to_str(org_id))

    def list_org_name(self):
        org_list = self.call_contract_command(
            "Registry", "listOrganizations", [])

        self._printout("# OrgName OrgId")
        for idx, org_id in enumerate(org_list):
            rez = self.call_contract_command(
                "Registry", "getOrganizationById", [org_id])
            if not rez[0]:
                raise Exception(
                    "Organization was removed during this call. Please retry.")
            org_name = rez[2]
            self._printout("%s  %s" % (org_name, bytes32_to_str(org_id)))

    def error_organization_not_found(self, org_id, found):
        if not found:
            raise Exception(
                "Organization with id={} doesn't exist!\n".format(org_id))

    def info(self):
        org_id = self.args.org_id
        (found, org_id, org_name, owner, members, serviceNames) = self._get_organization_by_id(org_id)
        self.error_organization_not_found(self.args.org_id, found)

        org_m = self._get_organization_metadata_from_registry(web3.Web3.to_text(org_id))
        org_name = org_m.org_name
        org_type = org_m.org_type
        description = org_m.description.get("description", "")

        self._printout("\nOrganization Name:\n - %s" % org_name)
        self._printout("\nId:\n - %s" % bytes32_to_str(org_id))
        self._printout("\nType:\n - %s" % org_type)
        self._printout("\nDescription:\n - %s" % description)

        if members:
            self._printout("\nMembers:")
            for idx, member in enumerate(members):
                self._printout(" - {}".format(member))
        if serviceNames:
            self._printout("\nServices:")
            for idx, service in enumerate(serviceNames):
                self._printout(" - {}".format(bytes32_to_str(service)))

    def metadata_validate(self):
        self._metadata_validate(as_exception=False)

    def _metadata_validate(self, as_exception=True):
        validation_res = self._metadata_validate_with_schema()
        if validation_res["status"] == 2:
            if as_exception:
                raise Exception(validation_res["msg"])
            else:
                self._printout(validation_res["msg"])
                exit(1)
        with open(self.args.metadata_file, 'r') as f:
            org_metadata = OrganizationMetadata.from_json(json.load(f), False)

        occurred_errors = []
        unique_group_names = set([group.group_name for group in org_metadata.groups])
        if len(unique_group_names) != len(org_metadata.groups):
            occurred_errors.append("There should be no groups with duplicated names in the metadata file.")

        for group in org_metadata.groups:
            for i, endpoint in enumerate(group.payment.payment_channel_storage_client.endpoints):
                if not is_valid_url(endpoint):
                    occurred_errors.append(f"Invalid endpoint `{endpoint}` at index {i} in group `{group.group_name}`.")

        existing_errors = validation_res.get("n_errors", 0)

        docs = "https://dev.singularitynet.io/docs/products/DecentralizedAIPlatform/CLI/Manual/Organization/"
        hint_message = f"\nVisit {docs} for more information."
        hint_message = f"\n{len(occurred_errors) + existing_errors} errors found." + hint_message + "\n"

        res_msg = ""
        for i in range(len(occurred_errors)):
            res_msg += str(existing_errors + i + 1) + ". " + occurred_errors[i] + "\n"

        if res_msg:
            if validation_res["status"] == 0:
                res_msg = "\nErrors found in the metadata file:\n" + res_msg
            else:
                res_msg = validation_res["msg"] + res_msg
            res_msg += hint_message
        elif validation_res["status"] == 0:
            res_msg = validation_res["msg"]
        else:
            res_msg = validation_res["msg"] + hint_message

        if as_exception and not res_msg.startswith("Organization metadata is valid and ready to publish."):
            raise Exception(res_msg)
        elif not as_exception:
            self._printout(res_msg)

    def _metadata_validate_with_schema(self):
        current_path = Path(__file__).parent
        relative_path = '../resources/org_schema.json'
        path_to_schema = (current_path / relative_path).resolve()
        with open(path_to_schema, 'r') as f:
            schema = json.load(f)

        metadata_file = self.args.metadata_file
        try:
            with open(metadata_file, 'r') as f:
                metadata_dict = json.load(f)
        except Exception as e:
                return {"status": 2, "msg": "Organization metadata json file not found, please check --metadata-file path"}

        validator = jsonschema.Draft7Validator(schema)
        occurred_errors = list(validator.iter_errors(metadata_dict))

        def get_path(err):
            return " -> ".join(f"`{el}`" for el in err.path)

        if len(occurred_errors) > 0:
            res_msg = f"\nErrors found in the metadata file:\n"
            for i, e in enumerate(occurred_errors):
                res_msg += str(i + 1) + ". "
                if e.validator == 'additionalProperties':
                    if len(e.path) != 0:
                        res_msg += f"{e.message} in {get_path(e)}."
                    else:
                        res_msg += f"{e.message} in main object."
                elif e.validator in ['required', 'type', 'enum', 'pattern', 'minLength', 'minItems']:
                    res_msg += f"{get_path(e)} - {e.message}"
                    if e.validator == 'minItems':
                        res_msg += f" (minimum 1 item required)"
                elif e.validator == 'maxLength':
                    res_msg += f"{get_path(e)} - string is too long"
                else:
                    res_msg += e.message
                res_msg += "\n"

            return {"status": 1, "msg": res_msg, "n_errors": len(occurred_errors)}
        else:
            return {"status": 0, "msg": "Organization metadata is valid and ready to publish."}

    def create(self):
        self._metadata_validate()

        metadata_file = self.args.metadata_file
        with open(metadata_file, 'r') as f:
            org_metadata = OrganizationMetadata.from_json(json.load(f))

        org_id = self.args.org_id

        # R Check if Organization already exists
        found = self._get_organization_by_id(org_id)[0]
        if found:
            raise Exception(
                "\nOrganization with id={} already exists!\n".format(org_id))

        members = self.get_members_from_args()

        storage = self.args.storage
        if not storage or storage == "ipfs":
            metadata_uri = publish_file_in_ipfs(self._get_ipfs_client(), metadata_file, False)
        elif storage == "filecoin":
            # upload to Filecoin via Lighthouse SDK
            metadata_uri = publish_file_in_filecoin(self._get_filecoin_client(), metadata_file)
        else:
            raise ValueError(f"Unsupported storage option: {storage}. Use --storage <ipfs or filecoin>")

        params = [type_converter("bytes32")(org_id),
                  hash_to_bytesuri(metadata_uri, storage), members]
        self._printout("Creating transaction to create organization name={} id={}\n".format(
            org_metadata.org_name, org_id))
        self.transact_contract_command(
            "Registry", "createOrganization", params)
        self._printout("id:\n%s" % org_id)

    def delete(self):
        org_id = self.args.org_id
        # Check if Organization exists
        (found, _, org_name, _, _, _) = self._get_organization_by_id(org_id)
        self.error_organization_not_found(org_id, found)

        self._printout("Creating transaction to delete organization with name={} id={}".format(
            org_name, org_id))
        try:
            self.transact_contract_command("Registry", "deleteOrganization", [
                type_converter("bytes32")(org_id)])
        except Exception as e:
            self._printerr(
                "\nTransaction error!\nHINT: Check if you are the owner of organization with id={}\n".format(org_id))
            raise

    def update_metadata(self):

        self._metadata_validate()

        metadata_file = self.args.metadata_file
        with open(metadata_file, 'r') as f:
            org_metadata = OrganizationMetadata.from_json(json.load(f))

        org_id = self.args.org_id
        existing_registry_org_metadata = self._get_organization_metadata_from_registry(org_id)
        org_metadata.check_remove_groups(existing_registry_org_metadata)

        # Check if Organization already exists
        found = self._get_organization_by_id(org_id)[0]
        if not found:
            raise Exception("\nOrganization with id={} does not exist!\n".format(org_id))

        storage = self.args.storage
        if not storage or storage == "ipfs":
            metadata_uri = publish_file_in_ipfs(self._get_ipfs_client(), metadata_file, False)
        elif storage == "filecoin":
            # upload to Filecoin via Lighthouse SDK
            metadata_uri = publish_file_in_filecoin(self._get_filecoin_client(), metadata_file)
        else:
            raise ValueError(f"Unsupported storage option: {storage}. Use --storage <ipfs or filecoin>")

        params = [type_converter("bytes32")(org_id), hash_to_bytesuri(metadata_uri, storage)]
        self._printout(
            "Creating transaction to update organization metadata for org name={} id={}\n".format(org_metadata.org_name,
                                                                                                  org_id))
        self.transact_contract_command("Registry", "changeOrganizationMetadataURI", params)
        self._printout("Organization updated successfully with id:\n%s" % org_id)

    def list_services(self):
        org_id = self.args.org_id
        (found, org_service_list) = self.call_contract_command("Registry", "listServicesForOrganization",
                                                               [type_converter("bytes32")(org_id)])
        self.error_organization_not_found(org_id, found)
        if org_service_list:
            self._printout("\nList of {}'s Services:".format(org_id))
            for idx, org_service in enumerate(org_service_list):
                self._printout("- {}".format(bytes32_to_str(org_service)))
        else:
            self._printout(
                "Organization with id={} exists but has no registered services.".format(org_id))

    def change_owner(self):
        org_id = self.args.org_id
        # Check if Organization exists
        (found, _, _, owner, _, _) = self._get_organization_by_id(org_id)
        self.error_organization_not_found(org_id, found)

        new_owner = self.args.owner
        if not web3.Web3.is_checksum_address(new_owner):
            raise Exception(
                "New owner account %s is not a valid Ethereum checksum address" % new_owner)

        if new_owner.lower() == owner.lower():
            raise Exception(
                "\n{} is the owner of Organization with id={}!\n".format(new_owner, org_id))

        self._printout(
            "Creating transaction to change organization {}'s owner...\n".format(org_id))
        try:
            self.transact_contract_command("Registry", "changeOrganizationOwner",
                                           [type_converter("bytes32")(org_id), self.args.owner])
        except Exception as e:
            self._printerr(
                "\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(org_id))
            raise

    def add_members(self):
        org_id = self.args.org_id
        # Check if Organization exists and member is not part of it
        (found, _, _, _, members, _) = self._get_organization_by_id(org_id)
        self.error_organization_not_found(org_id, found)

        members = [member.lower() for member in members]
        add_members = []
        for add_member in self.get_members_from_args():
            if add_member.lower() in members:
                self._printout(
                    "{} is already a member of organization {}".format(add_member, org_id))
            else:
                add_members.append(add_member)

        if not add_members:
            self._printout("No member was added to {}!\n".format(org_id))
            return

        params = [type_converter("bytes32")(org_id), add_members]
        self._printout(
            "Creating transaction to add {} members into organization {}...\n".format(len(add_members), org_id))
        try:
            self.transact_contract_command(
                "Registry", "addOrganizationMembers", params)
        except Exception as e:
            self._printerr(
                "\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(org_id))
            raise

    def rem_members(self):
        org_id = self.args.org_id
        # Check if Organization exists and member is part of it
        (found, _, _, _, members, _) = self._get_organization_by_id(org_id)
        self.error_organization_not_found(org_id, found)

        members = [member.lower() for member in members]
        rem_members = []
        for rem_member in self.get_members_from_args():
            if rem_member.lower() not in members:
                self._printout(
                    "{} is not a member of organization {}".format(rem_member, org_id))
            else:
                rem_members.append(rem_member)

        if not rem_members:
            self._printout("No member was removed from {}!\n".format(org_id))
            return

        params = [type_converter("bytes32")(org_id), rem_members]
        self._printout(
            "Creating transaction to remove {} members from organization with id={}...\n".format(len(rem_members),
                                                                                                 org_id))
        try:
            self.transact_contract_command(
                "Registry", "removeOrganizationMembers", params)
        except Exception as e:
            self._printerr(
                "\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(org_id))
            raise

    def list_my(self):
        """ Find organization that has the current identity as the owner or as the member """
        org_list = self.call_contract_command(
            "Registry", "listOrganizations", [])

        rez_owner = []
        rez_member = []
        for idx, org_id in enumerate(org_list):
            (found, org_id, org_name, owner, members, serviceNames) = self.call_contract_command(
                "Registry", "getOrganizationById", [org_id])
            if not found:
                raise Exception(
                    "Organization was removed during this call. Please retry.")
            if self.ident.address == owner:
                rez_owner.append((org_name, bytes32_to_str(org_id)))

            if self.ident.address in members:
                rez_member.append((org_name, bytes32_to_str(org_id)))

        if rez_owner:
            self._printout("# Organizations you are the owner of")
            self._printout("# OrgName OrgId")
            for n, i in rez_owner:
                self._printout("%s   %s" % (n, i))

        if rez_member:
            self._printout("# Organizations you are the member of")
            self._printout("# OrgName OrgId")
            for n, i in rez_member:
                self._printout("%s   %s" % (n, i))

    def metadata_add_asset_to_ipfs(self):
        metadata_file = self.args.metadata_file
        org_metadata = OrganizationMetadata.from_file(metadata_file)
        asset_file_ipfs_hash_base58 = publish_file_in_ipfs(self._get_ipfs_client(),
                                                           self.args.asset_file_path)

        org_metadata.add_asset(asset_file_ipfs_hash_base58, self.args.asset_type)
        org_metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_assets_of_a_given_type(self):
        metadata_file = self.args.metadata_file
        org_metadata = OrganizationMetadata.from_file(metadata_file)
        org_metadata.remove_assets(self.args.asset_type)
        org_metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_all_assets(self):
        metadata_file = self.args.metadata_file
        org_metadata = OrganizationMetadata.from_file(metadata_file)
        org_metadata.remove_all_assets()
        org_metadata.save_pretty(self.args.metadata_file)

    def metadata_add_description(self):
        description = self.args.description
        url = self.args.url
        short_description = self.args.short_description
        metadata_file = self.args.metadata_file
        org_metadata = OrganizationMetadata.from_file(metadata_file)
        if description:
            org_metadata.add_description(description)
        if short_description:
            org_metadata.add_short_description(short_description)
        if url:
            org_metadata.add_url(url)
        if description is None and url is None and short_description is None:
            raise Exception("No attributes are given")
        org_metadata.save_pretty(metadata_file)

    def metadata_add_contact(self):
        args = self.args.__dict__
        metadata_file = args["metadata_file"]
        contact_type = args.get("contact_type", None)
        phone = args.get("phone", None)
        email = args.get("email", None)
        if phone is None and email is None:
            self._printout("email and phone both can not be empty")
        else:
            org_metadata = OrganizationMetadata.from_file(metadata_file)
            org_metadata.add_contact(contact_type, phone, email)
            org_metadata.save_pretty(metadata_file)

    def metadata_remove_contact_by_type(self):
        metadata_file = self.args.metadata_file
        contact_type = self.args.contact_type
        org_metadata = OrganizationMetadata.from_file(metadata_file)
        org_metadata.remove_contact_by_type(contact_type)
        org_metadata.save_pretty(metadata_file)

    def metadata_remove_all_contacts(self):
        metadata_file = self.args.metadata_file
        org_metadata = OrganizationMetadata.from_file(metadata_file)
        org_metadata.remove_all_contacts()
        org_metadata.save_pretty(metadata_file)
