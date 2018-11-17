import getpass
import io
import json
import os
import shlex
import sys
import tarfile
import tempfile
from pathlib import Path
from shutil import rmtree
from textwrap import indent
from urllib.parse import urljoin

import grpc
import ipfsapi
import requests
import yaml
from google.protobuf import json_format
from rfc3986 import urlparse, uri_reference

from snet_cli.contract import Contract
from snet_cli.identity import get_kws_for_identity_type, get_identity_types
from snet_cli.session import from_config, get_session_keys
from snet_cli.utils import DefaultAttributeObject, get_web3, get_identity, serializable, walk_imports, \
    read_temp_tar, type_converter, get_contract_def, get_cli_version, compile_proto


class Command(object):
    def __init__(self, config, args, out_f=sys.stdout, err_f=sys.stderr):
        self.config = config
        self.session = from_config(self.config)
        self.args = args
        self.out_f = out_f
        self.err_f = err_f
        if self.config.getboolean("session", "init", fallback=False):
            del self.config["session"]["init"]
            InitCommand(self.config, self.args, self.out_f, self.err_f).init()
            self.session = from_config(self.config)
            if (self.args.cmd.__name__ == "IdentityCommand" and self.args.fn == "create" and
                    self.args.identity_name == self.config["session"]["identity_name"]):
                self.args.fn = "_nothing"

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
        if self._getboolean("verbose"):
            self._pprint({"receipt": receipt, "events": events})
        elif self._getboolean("quiet"):
            self._pprint({"transactionHash": receipt["transactionHash"]})
        else:
            self._pprint({"receipt_summary": {"blockHash": receipt["blockHash"],
                                              "blockNumber": receipt["blockNumber"],
                                              "cumulativeGasUsed": receipt["cumulativeGasUsed"],
                                              "gasUsed": receipt["gasUsed"],
                                              "transactionHash": receipt["transactionHash"]},
                          "event_summaries": [{"args": e["args"], "event": e["event"]} for e in events]})

    def _getstring(self, name):
        return (self.session.identity.getstring(name) or getattr(self.args, name, None) or
                (self.session.getstring("default_{}".format(name)) or
                 self.session.getstring("current_{}".format(name))))

    def _getint(self, name):
        return (self.session.identity.getint(name) or getattr(self.args, name, None) or
                (self.session.getint("default_{}".format(name)) or
                 self.session.getint("current_{}".format(name))))

    def _getfloat(self, name):
        return (self.session.identity.getfloat(name) or getattr(self.args, name, None) or
                (self.session.getfloat("default_{}".format(name)) or
                 self.session.getfloat("current_{}".format(name))))

    def _getboolean(self, name):
        return (self.session.identity.getboolean(name) or getattr(self.args, name, None) or
                (self.session.getboolean("default_{}".format(name)) or
                 self.session.getboolean("current_{}".format(name))))

    def _get_ipfs_client(self):
        ipfs_endpoint = urlparse(self.config["ipfs"]["default_ipfs_endpoint"])
        ipfs_scheme = ipfs_endpoint.scheme if ipfs_endpoint.scheme else "http"
        ipfs_port = ipfs_endpoint.port if ipfs_endpoint.port else 5001
        return ipfsapi.connect(urljoin(ipfs_scheme, ipfs_endpoint.hostname), ipfs_port)

    def _set_key(self, key, value, config=None, out_f=None, err_f=None):
        SessionCommand(config or self.config, DefaultAttributeObject(key=key, value=value), out_f or self.out_f,
                       err_f or self.err_f).set()

    def _unset_key(self, key, config=None, out_f=None, err_f=None):
        SessionCommand(config or self.config, DefaultAttributeObject(key=key), out_f or self.out_f,
                       err_f or self.err_f).unset()

    def _nothing(self):
        pass


class VersionCommand(Command):
    def show(self):
        self._pprint({"version": get_cli_version()})


class BlockchainCommand(Command):
    def __init__(self, config, args, out_f=sys.stdout, err_f=sys.stderr, w3=None, ident=None):
        super(BlockchainCommand, self).__init__(config, args, out_f, err_f)
        self.w3 = w3 or get_web3(self._getstring("eth_rpc_endpoint"))
        self.ident = ident or get_identity(self.w3, self.session, self.args)

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
                                             contract_def      = contract_def)(*contract_params),
                               out_f = out_f,
                               err_f = out_f,
                               w3    = self.w3,
                               ident = self.ident)

    def call_contract_command(self, contract_name, contract_address, contract_fn, contract_params, is_silent = True):
        return self.get_ContractCommand(contract_name, contract_address, contract_fn, contract_params, is_silent).call()

    def transact_contract_command(self, contract_name, contract_address, contract_fn, contract_params, is_silent = False):
        return self.get_ContractCommand(contract_name, contract_address, contract_fn, contract_params, is_silent).transact()

class InitCommand(Command):
    def init(self):
        self._printout("Create your first identity. This will be used to authenticate and sign requests pertaining\n"
                       "to the blockchain.\n"
                       "\n"
                       "The available identity types are:\n"
                       "    - 'rpc' (yields to a required ethereum json-rpc endpoint for signing using a given wallet\n"
                       "          index)\n"
                       "    - 'mnemonic' (uses a required bip39 mnemonic for HDWallet/account derivation and signing\n"
                       "          using a given wallet index)\n"
                       "    - 'key' (uses a required hex-encoded private key for signing)\n"
                       "    - 'ledger' (yields to a required ledger nano s device for signing using a given wallet\n"
                       "          index)\n"
                       "    - 'trezor' (yields to a required trezor device for signing using a given wallet index)\n"
                       "\n"
                       "Create additional identities by running 'snet identity create', and switch identities by \n"
                       "running 'snet identity <identity_name>'.\n")
        create_identity_kwargs = {}
        identity_name = getattr(self.args, "identity_name", None) or input("Choose a name for your first identity: \n") or None
        self._ensure(identity_name is not None, "identity name is required")
        create_identity_kwargs["identity_name"] = identity_name
        identity_type = getattr(self.args, "identity_type", None) or input("Select an identity type for your first"
                                                  " identity (choose from {}): \n".format(get_identity_types())) or None
        self._ensure(identity_type in get_identity_types(),
                     "identity type {} not in {}".format(identity_type, get_identity_types()))
        create_identity_kwargs["identity_type"] = identity_type
        for kw, is_secret in get_kws_for_identity_type(identity_type):
            kw_prompt = "{}: \n".format(" ".join(kw.capitalize().split("_")))
            if is_secret:
                value = getattr(self.args, kw, None) or getpass.getpass(kw_prompt) or None
            else:
                value = getattr(self.args, kw, None) or input(kw_prompt) or None
            self._ensure(value is not None, "{} is required".format(kw.split("_")))
            create_identity_kwargs[kw] = value
        IdentityCommand(self.config, DefaultAttributeObject(**create_identity_kwargs), self.err_f, self.err_f).create()
        self._set_key("identity_name", identity_name, out_f=self.err_f)


class IdentityCommand(Command):
    def create(self):
        identity = {}

        identity_name = self.args.identity_name
        self._ensure(not self.config.has_section("identity.{}".format(identity_name)),
                     "identity_name {} already in use".format(identity_name))

        identity_type = self.args.identity_type
        identity["identity_type"] = identity_type

        for kw, is_secret in get_kws_for_identity_type(identity_type):
            value = getattr(self.args, kw)
            if value is None and is_secret:
                kw_prompt = "{}: ".format(" ".join(kw.capitalize().split("_")))
                value = getpass.getpass(kw_prompt) or None
            self._ensure(value is not None, "--{} is required for identity_type {}".format(kw, identity_type))
            identity[kw] = value

        self.config["identity.{}".format(identity_name)] = identity
        self.config.persist()

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
        identity_name = self.args.identity_name
        self._ensure(self.config.has_section("identity.{}".format(identity_name)),
                     "identity_name {} does not exist".format(identity_name))
        self._ensure(self.config.get("session", "identity_name", fallback="") != identity_name,
                     "identity_name {} is in use".format(identity_name))

        self.config.remove_section("identity.{}".format(identity_name))
        self.config.persist()

    def set(self):
        identity_name = self.args.identity_name
        self._ensure(self.config.has_section("identity.{}".format(identity_name)),
                     "identity_name {} does not exist".format(identity_name))
        self._set_key("identity_name", identity_name)


class NetworkCommand(Command):
    def list(self):
        for network_section in filter(lambda x: x.startswith("network."), self.config.sections()):
            network = self.config[network_section]
            self._pprint({network_section[len("network."):]: {k: v for k, v in network.items()}})

    def set(self):
        network_name = self.args.network_name
        self._ensure(self.config.has_section("network.{}".format(network_name)) or network_name == "eth_rpc_endpoint",
                     "network_name {} does not exist".format(network_name))
        if network_name != "eth_rpc_endpoint":
            for k, v in self.config["network.{}".format(network_name)].items():
                self._set_key(k, v)
        else:
            self._ensure(self.args.eth_rpc_endpoint.startswith("http"), "eth rpc endpoint must start with http")
            self._set_key("default_eth_rpc_endpoint", self.args.eth_rpc_endpoint)


class SessionCommand(Command):
    def set(self):
        key = self.args.key

        self._ensure(key in get_session_keys(), "key {} not in {}".format(key, get_session_keys()))

        value = self.args.value

        if key == "default_eth_rpc_endpoint":
            self._ensure(self.session.identity.identity_type != "rpc",
                         "cannot set default_eth_rpc_endpoint while using rpc identity_type")
            to_delete = []
            for k in self.config["session"]:
                if k[-3:] == "_at":
                    to_delete.append(k)
            for k in to_delete:
                del self.config["session"][k]
                self._printerr("unset {}\n".format(k))

        if key == "identity_name":
            self._ensure(self.config.has_section("identity.{}".format(value)),
                         "identity_name {} does not exist".format(value))
            identity = self.config["identity.{}".format(value)]
            for k, _ in identity.items():
                try:
                    del self.config["session"]["default_{}".format(k)]
                    self._printerr("unset default_{}\n".format(k))
                except KeyError:
                    pass

        self.config["session"][key] = value
        self.config.persist()
        self._printout("set {} {}\n".format(key, value))

    def unset(self):
        key = self.args.key

        self._ensure(key in get_session_keys(), "key {} not in {}".format(key, get_session_keys()))

        try:
            del self.config["session"][key]
            self.config.persist()
            self._printout("unset {}\n".format(key))
        except KeyError:
            pass

    def show(self):
        self._pprint({"session": dict(self.config["session"])})


class ContractCommand(BlockchainCommand):
    def call(self):
        contract_address = self._getstring("at")

        if contract_address is None:
            networks = self.args.contract_def["networks"]
            chain_id = self.w3.version.network
            contract_address = networks.get(chain_id, {}).get("address", None)

        self._ensure(contract_address is not None, "--at is required to specify target contract address")

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
        contract_address = self.args.at

        if contract_address is None:
            networks = self.args.contract_def["networks"]
            chain_id = self.w3.version.network
            contract_address = networks.get(chain_id, {}).get("address", None)

        self._ensure(contract_address is not None, "--at is required to specify target contract address")

        abi = self.args.contract_def["abi"]

        contract = Contract(self.w3, contract_address, abi)

        positional_inputs = getattr(self.args, "contract_positional_inputs", [])
        named_inputs = {
            name[len("contract_named_input_"):]: value for name, value
            in self.args.__dict__.items() if name.startswith("contract_named_input_")
        }

        gas_price = self._getint("gas_price")
        self._ensure(gas_price is not None, "--gas-price required to transact")

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
        registry_contract_def = get_contract_def("Registry")
        registry_address = self._getstring("registry_at")
        try:
            return ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=registry_address,
                    contract_function="getOrganizationByName",
                    contract_def=registry_contract_def)(type_converter("bytes32")(self.args.name)),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()

        except Exception as e:
            self._printerr("\nCall _getorganizationbyname() error!\nHINT: Check your identity and session.\n")
            self._error(e)

    def list(self):
        try:
            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")
            org_list = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=registry_address,
                    contract_function="listOrganizations",
                    contract_def=registry_contract_def)(),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()

            self._printerr("\nList of Organizations:")
            for idx, organization in enumerate(org_list):
                self._printerr("- {}".format(organization.partition(b"\0")[0].decode("utf-8")))

        except Exception as e:
            self._printerr("\nCall error!\nHINT: Check your identity and session.\n")
            self._error(e)

    def info(self):
        try:
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

        except Exception as e:
            self._printerr("\nCall error!\nHINT: Check your identity and session.\n")
            self._error(e)

    def create(self):
        try:
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

            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")
            cmd = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=registry_address,
                    contract_function="createOrganization",
                    contract_def=registry_contract_def)(type_converter("bytes32")(self.args.name),
                                                        [type_converter("address")(member) for member in members]),
                out_f=self.err_f,
                err_f=self.err_f,
                w3=self.w3,
                ident=self.ident)
            self._printerr("Creating transaction to create organization {}...\n".format(self.args.name))
            try:
                cmd.transact()
            except Exception as e:
                self._printerr("\nTransaction error!\nHINT: Check if {} already exists.\n".format(self.args.name))
                self._error(e)

        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if address is a 40-length hexadecimal.\n")
            self._error(e)

    def delete(self):
        try:
            # Check if Organization exists
            (found, _, _, _, _, _) = self._getorganizationbyname()
            if not found:
                self._printerr("\n{} doesn't exist!\n".format(self.args.name))
                return

            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")
            cmd = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=registry_address,
                    contract_function="deleteOrganization",
                    contract_def=registry_contract_def)(type_converter("bytes32")(self.args.name)),
                out_f=self.err_f,
                err_f=self.err_f,
                w3=self.w3,
                ident=self.ident)
            self._printerr("Creating transaction to delete organization {}...\n".format(self.args.name))
            try:
                cmd.transact()
            except Exception as e:
                self._printerr("\nTransaction error!\nHINT: Check if {} exists and you are its owner.\n".format(self.args.name))
                self._error(e)

        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check ORG_NAME.\n")
            self._error(e)

    def list_services(self):
        try:
            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")
            try:
                (found, org_service_list) = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=registry_address,
                        contract_function="listServicesForOrganization",
                        contract_def=registry_contract_def)(type_converter("bytes32")(self.args.name)),
                    out_f=None,
                    err_f=None,
                    w3=self.w3,
                    ident=self.ident).call()

                if found:
                    if org_service_list:
                        self._printerr("\nList of {}'s Services:".format(self.args.name))
                        for idx, org_service in enumerate(org_service_list):
                            self._printerr("- {}".format(org_service.partition(b"\0")[0].decode("utf-8")))
                    else:
                        self._printerr("\n{} exists but has no registered services.".format(self.args.name))
                else:
                    self._printerr("\n{} not registered on network.".format(self.args.name))

            except Exception as e:
                self._printerr("\nCall error!\nHINT: Check your identity and session.\n")
                self._error(e)

        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check ORG_NAME.\n")
            self._error(e)

    def change_owner(self):
        try:
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

            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")
            cmd = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=registry_address,
                    contract_function="changeOrganizationOwner",
                    contract_def=registry_contract_def)(type_converter("bytes32")(self.args.name),
                                                        type_converter("address")(self.args.owner)),
                out_f=self.err_f,
                err_f=self.err_f,
                w3=self.w3,
                ident=self.ident)
            self._printerr("Creating transaction to change organization {}'s owner...\n".format(self.args.name))
            try:
                cmd.transact()
            except Exception as e:
                self._printerr("\nTransaction error!\nHINT: Check if {} already exists.\n".format(self.args.name))
                self._error(e)

        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if address is a 40-length hexadecimal.\n")
            self._error(e)

    def add_members(self):
        try:
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

            if add_members:
                registry_contract_def = get_contract_def("Registry")
                registry_address = self._getstring("registry_at")
                cmd = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=registry_address,
                        contract_function="addOrganizationMembers",
                        contract_def=registry_contract_def)(type_converter("bytes32")(self.args.name),
                                                            [type_converter("address")(member) for member in add_members]),
                    out_f=self.err_f,
                    err_f=self.err_f,
                    w3=self.w3,
                    ident=self.ident)
                self._printerr("Creating transaction to add {} members into organization {}...\n".format(len(add_members), self.args.name))
                try:
                    cmd.transact()
                except Exception as e:
                    self._printerr("\nTransaction error!\nHINT: Check if {} already exists and you are its owner.\n".format(self.args.name))
                    self._error(e)
            else:
                self._printerr("No member was added to {}!\n".format(self.args.name))

        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if address is a 40-length hexadecimal.\n")
            self._error(e)

    def rem_members(self):
        try:
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

            if rem_members:
                registry_contract_def = get_contract_def("Registry")
                registry_address = self._getstring("registry_at")
                cmd = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=registry_address,
                        contract_function="removeOrganizationMembers",
                        contract_def=registry_contract_def)(type_converter("bytes32")(self.args.name),
                                                            [type_converter("address")(member) for member in rem_members]),
                    out_f=self.err_f,
                    err_f=self.err_f,
                    w3=self.w3,
                    ident=self.ident)
                self._printerr("Creating transaction to remove {} members from organization {}...\n".format(len(rem_members), self.args.name))
                try:
                    cmd.transact()
                except Exception as e:
                    self._printerr("\nTransaction error!\nHINT: Check if {} already exists and you are its owner.\n".format(self.args.name))
                    self._error(e)
            else:
                self._printerr("No member was removed from {}!\n".format(self.args.name))

        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if address is a 40-length hexadecimal.\n")
            self._error(e)
