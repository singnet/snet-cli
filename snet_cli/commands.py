import getpass
import json
import sys
from textwrap import indent
from urllib.parse import urljoin

import ipfsapi
import yaml
from rfc3986 import urlparse

from snet_cli.contract import Contract
from snet_cli.identity import get_kws_for_identity_type, get_identity_types
from snet_cli.utils import DefaultAttributeObject, get_web3, serializable, type_converter, get_contract_def, get_cli_version

from snet_cli.config import get_session_identity_keys, get_session_network_keys
from snet_cli.utils_config import get_contract_address, get_field_from_args_or_session
from snet_cli.identity import RpcIdentityProvider, MnemonicIdentityProvider, TrezorIdentityProvider, \
    LedgerIdentityProvider, KeyIdentityProvider


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

    def _printout(self, message):
        if self.out_f is not None:
            print(message, file=self.out_f)

    def _printerr(self, message):
        if self.err_f is not None:
            print(message, file=self.err_f)

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
        ipfs_endpoint = urlparse(self.config.get_ipfs_endpoint())
        ipfs_scheme = ipfs_endpoint.scheme if ipfs_endpoint.scheme else "http"
        ipfs_port = ipfs_endpoint.port if ipfs_endpoint.port else 5001
        return ipfsapi.connect(urljoin(ipfs_scheme, ipfs_endpoint.hostname), ipfs_port)

class VersionCommand(Command):
    def show(self):
        self._pprint({"version": get_cli_version()})


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

    def get_gas_price(self):
        return int(get_field_from_args_or_session(self.config, self.args, "gas_price"))

    def get_mpe_address(self):
        return get_contract_address(self, "MultiPartyEscrow")

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

    def get_ContractCommand(self, contract_name, contract_address, contract_fn, contract_params, is_silent = True):
        contract_def = get_contract_def(contract_name)
        if (is_silent):
            out_f = None
        else:
            out_f = self.err_f
        return ContractCommand(config= self.config,
                               args  = self.get_contract_argser(
                                             contract_address  = contract_address,
                                             contract_function = contract_fn,
                                             contract_def      = contract_def,
                                             contract_name     = contract_name)(*contract_params),
                               out_f = out_f,
                               err_f = out_f,
                               w3    = self.w3,
                               ident = self.ident)

    def call_contract_command(self, contract_name, contract_fn, contract_params, is_silent = True):
        contract_address = get_contract_address(self, contract_name)
        return self.get_ContractCommand(contract_name, contract_address, contract_fn, contract_params, is_silent).call()

    def transact_contract_command(self, contract_name, contract_fn, contract_params, is_silent = False):
        contract_address = get_contract_address(self, contract_name)
        return self.get_ContractCommand(contract_name, contract_address, contract_fn, contract_params, is_silent).transact()


class IdentityCommand(Command):
    def create(self):
        identity = {}

        identity_name = self.args.identity_name
        self._ensure(not identity_name in self.config.get_all_identies_names(), "identity_name {} already exists".format(identity_name))

        identity_type = self.args.identity_type
        identity["identity_type"] = identity_type

        for kw, is_secret in get_kws_for_identity_type(identity_type):
            value = getattr(self.args, kw)
            if value is None and is_secret:
                kw_prompt = "{}: ".format(" ".join(kw.capitalize().split("_")))
                value = getpass.getpass(kw_prompt) or None
            self._ensure(value is not None, "--{} is required for identity_type {}".format(kw, identity_type))
            identity[kw] = value

        if (self.args.network):
            identity["network"] = self.args.network
        identity["default_wallet_index"] = self.args.wallet_index
        self.config.add_identity(identity_name, identity, self.out_f)

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
            self._pprint({network_section[len("network."):]: {k: v for k, v in network.items()}})

    def create(self):
        # check endpoint by getting its network_id
        w3         = get_web3(self.args.eth_rpc_endpoint)
        network_id = w3.version.network

        self._printout("add network with name='%s' with networkId='%s'"%(self.args.network_name, str(network_id)))
        self.config.add_network(self.args.network_name, self.args.eth_rpc_endpoint, self.args.default_gas_price)
    def set(self):
        self.config.set_session_network(self.args.network_name, self.out_f)


class SessionCommand(Command):
    def set(self):
        self.config.set_session_field(self.args.key, self.args.value, self.out_f)

    def unset(self):
        self.config.unset_session_field(self.args.key, self.out_f)

    def show(self):
        rez = self.config.session_to_dict()

        # we don't want to who private_key and mnemonic
        for d in rez.values():
            d.pop("private_key", None)
            d.pop("mnemonic", None)
        self._pprint(rez)


class ContractCommand(BlockchainCommand):
    def call(self):
        contract_address = get_contract_address(self, self.args.contract_name, "--at is required to specify target contract address")

        abi = self.args.contract_def["abi"]

        contract = Contract(self.w3, contract_address, abi)

        positional_inputs = getattr(self.args, "contract_positional_inputs", [])
        named_inputs = {
            name[len("contract_named_input_"):]: value for name, value
            in self.args.__dict__.items() if name.startswith("contract_named_input_")
        }

        result = contract.call(self.args.contract_function, *positional_inputs, **named_inputs)
        self._printout(result)
        return result

    def transact(self):
        contract_address = get_contract_address(self, self.args.contract_name, "--at is required to specify target contract address")

        abi = self.args.contract_def["abi"]

        contract = Contract(self.w3, contract_address, abi)

        positional_inputs = getattr(self.args, "contract_positional_inputs", [])
        named_inputs = {
            name[len("contract_named_input_"):]: value for name, value
            in self.args.__dict__.items() if name.startswith("contract_named_input_")
        }

        gas_price = self.get_gas_price()

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
    def _getorganizationbyname(self):
        return self.call_contract_command("Registry", "getOrganizationByName", [type_converter("bytes32")(self.args.name)])

    def list(self):
        org_list = self.call_contract_command("Registry", "listOrganizations", [])

        self._printerr("\nList of Organizations:")
        for idx, organization in enumerate(org_list):
            self._printerr("- {}".format(organization.partition(b"\0")[0].decode("utf-8")))

    def info(self):
        (found, name, owner, members, serviceNames, repositoryNames) = self._getorganizationbyname()

        if found:
            self._printerr("\nOwner:\n - {}".format(owner.lower()))
            if members:
                self._printerr("\nMembers:".format(self.args.name))
                for idx, member in enumerate(members):
                    self._printerr(" - {}".format(member.lower()))
            if serviceNames:
                self._printerr("\nServices:".format(self.args.name))
                for idx, service in enumerate(serviceNames):
                    self._printerr(" - {}".format(service.partition(b"\0")[0].decode("utf-8")))
            if repositoryNames:
                self._printerr("\nRepositories:".format(self.args.name))
                for idx, repo in enumerate(repositoryNames):
                    self._printerr(" - {}".format(repo.partition(b"\0")[0].decode("utf-8")))
        else:
            self._printerr("\n{} not registered on network.".format(self.args.name))


    def create(self):
        # Check if Organization already exists
        (found, _, _, _, _, _) = self._getorganizationbyname()
        if found:
            self._printerr("\n{} already exists!\n".format(self.args.name))
            return

        members = []
        if self.args.members:
            members_split = self.args.members.split(',')
            for idx, m in enumerate(members_split):
                members.append(str(m).replace("[", "").replace("]", "").lower())

        params = [type_converter("bytes32")(self.args.name), [type_converter("address")(member) for member in members]]
        self._printerr("Creating transaction to create organization {}...\n".format(self.args.name))
        self.transact_contract_command("Registry", "createOrganization", params)


    def delete(self):
        # Check if Organization exists
        (found, _, _, _, _, _) = self._getorganizationbyname()
        if not found:
            self._printerr("\n{} doesn't exist!\n".format(self.args.name))
            return

        self._printerr("Creating transaction to delete organization {}...\n".format(self.args.name))
        try:
            self.transact_contract_command("Registry", "deleteOrganization", [type_converter("bytes32")(self.args.name)])
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(self.args.name))
            raise

    def list_services(self):
        (found, org_service_list) = self.call_contract_command("Registry", "listServicesForOrganization", [type_converter("bytes32")(self.args.name)])
        if found:
            if org_service_list:
                self._printerr("\nList of {}'s Services:".format(self.args.name))
                for idx, org_service in enumerate(org_service_list):
                    self._printerr("- {}".format(org_service.partition(b"\0")[0].decode("utf-8")))
            else:
                self._printerr("\n{} exists but has no registered services.".format(self.args.name))
        else:
            self._printerr("\n{} not registered on network.".format(self.args.name))

    def change_owner(self):
        # Check if Organization exists
        (found, _, owner, _, _, _) = self._getorganizationbyname()
        if not found:
            self._printerr("\n{} doesn't exist!\n".format(self.args.name))
            return

        new_owner = self.args.owner.lower()
        new_owner = new_owner if new_owner.startswith("0x") else "0x" + new_owner
        if new_owner == owner:
            self._printerr("\n{} is the owner of!\n".format(self.args.owner, self.args.name))
            return

        self._printerr("Creating transaction to change organization {}'s owner...\n".format(self.args.name))
        try:
            self.transact_contract_command("Registry", "changeOrganizationOwner", [type_converter("bytes32")(self.args.name),                                                                                  type_converter("address")(self.args.owner)])
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(self.args.name))
            raise

    def add_members(self):
        # Check if Organization exists and member is not part of it
        (found, _, _, members, _, _) = self._getorganizationbyname()
        if not found:
            self._printerr("\n{} doesn't exist!\n".format(self.args.name))
            return

        add_members = []
        members_split = self.args.members.split(',')
        for idx, m in enumerate(members_split):
            member_tmp = str(m).replace("[", "").replace("]", "").lower()
            member_tmp = member_tmp if member_tmp.startswith("0x") else "0x" + member_tmp
            add_members.append(member_tmp)

        members = [member.lower() for member in members]

        for idx, add_member in enumerate(add_members[:]):
            if add_member in members:
                self._printerr("{} is already a member of organization {}".format(add_member, self.args.name))
                add_members.remove(add_member)

        if not add_members:
            self._printerr("No member was added to {}!\n".format(self.args.name))
            return

        params = [type_converter("bytes32")(self.args.name),
                 [type_converter("address")(member) for member in add_members]]
        self._printerr("Creating transaction to add {} members into organization {}...\n".format(len(add_members), self.args.name))
        try:
            self.transact_contract_command("Registry", "addOrganizationMembers", params)
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(self.args.name))
            raise

    def rem_members(self):
        # Check if Organization exists and member is part of it
        (found, _, _, members, _, _) = self._getorganizationbyname()
        if not found:
            self._printerr("\n{} doesn't exist!\n".format(self.args.name))
            return

        rem_members = []
        members_split = self.args.members.split(',')
        for idx, m in enumerate(members_split):
            member_tmp = str(m).replace("[", "").replace("]", "").lower()
            member_tmp = member_tmp if member_tmp.startswith("0x") else "0x" + member_tmp
            rem_members.append(member_tmp)

        members = [member.lower() for member in members]

        for idx, rem_member in enumerate(rem_members[:]):
            if rem_member not in members:
                self._printerr("{} is not a member of organization {}".format(rem_member, self.args.name))
                rem_members.remove(rem_member)

        if not rem_members:
            self._printerr("No member was removed from {}!\n".format(self.args.name))
            return
        params = [type_converter("bytes32")(self.args.name),
                 [type_converter("address")(member) for member in rem_members]]
        self._printerr("Creating transaction to remove {} members from organization {}...\n".format(len(rem_members), self.args.name))
        try:
            self.transact_contract_command("Registry", "removeOrganizationMembers", params)
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(self.args.name))
            raise
