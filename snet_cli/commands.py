import getpass
import json
import sys
from textwrap import indent
from urllib.parse import urljoin

import ipfsapi
import yaml
from rfc3986 import urlparse

from snet_cli.contract import Contract
from snet_cli.identity import get_kws_for_identity_type
from snet_cli.utils import DefaultAttributeObject, get_web3, serializable, type_converter, get_contract_def, get_cli_version, bytes32_to_str

from snet_cli.utils_config import get_contract_address, get_field_from_args_or_session
from snet_cli.identity import RpcIdentityProvider, MnemonicIdentityProvider, TrezorIdentityProvider, \
    LedgerIdentityProvider, KeyIdentityProvider, KeyStoreIdentityProvider
import web3
import secrets
import string


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
            err_f = None
        else:
            out_f = self.out_f
            err_f = self.err_f
        return ContractCommand(config= self.config,
                               args  = self.get_contract_argser(
                                             contract_address  = contract_address,
                                             contract_function = contract_fn,
                                             contract_def      = contract_def,
                                             contract_name     = contract_name)(*contract_params),
                               out_f = out_f,
                               err_f = err_f,
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
        self._ensure(not identity_name in self.config.get_all_identities_names(), "identity_name {} already exists".format(identity_name))

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
        network_id = None
        if (not self.args.skip_check):
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
    def _getorganizationbyid(self, org_id):
        org_id_bytes32 = type_converter("bytes32")(org_id)
        if (len(org_id_bytes32) > 32):
            raise Exception("Your org_id is too long, it should be 32 bytes or less. len(org_id_bytes32)=%i"%(len(org_id_bytes32)))
        return self.call_contract_command("Registry", "getOrganizationById", [org_id_bytes32])

    #TODO: It would be better to have standard nargs="+" in argparse for members.
    #      But we keep comma separated members for backward compatibility
    def get_members_from_args(self):
        if (not self.args.members):
            return []
        members = [m.replace("[", "").replace("]", "") for m in self.args.members.split(',')]
        for m in members:
            if not web3.eth.is_checksum_address(m):
                raise Exception("Member account %s is not a valid Ethereum checksum address"%m)
        return members

    def list(self):
        org_list = self.call_contract_command("Registry", "listOrganizations", [])

        self._printout("# OrgId")
        for idx, org_id in enumerate(org_list):
            self._printout(bytes32_to_str(org_id))

    def list_orgnames(self):
        org_list = self.call_contract_command("Registry", "listOrganizations", [])

        self._printout("# OrgName OrgId")
        for idx, org_id in enumerate(org_list):
            rez = self.call_contract_command("Registry", "getOrganizationById", [org_id])
            if (not rez[0]):
                raise Exception("Organization was removed during this call. Please retry.");
            org_name = rez[2]
            self._printout("%s  %s"%(org_name, bytes32_to_str(org_id)))

    def error_organization_not_found(self, org_id, found):
        if not found:
            raise Exception("Organization with id={} doesn't exist!\n".format(org_id))

    def info(self):
        org_id = self.args.org_id
        (found, org_id, org_name, owner, members, serviceNames, repositoryNames) = self._getorganizationbyid(org_id)
        self.error_organization_not_found(self.args.org_id, found)

        self._printout("\nOrganization Name:\n - %s"%org_name)
        self._printout("\nOrganization Id:\n - %s"%bytes32_to_str(org_id))
        self._printout("\nOwner:\n - {}".format(owner))
        if members:
            self._printout("\nMembers:")
            for idx, member in enumerate(members):
                self._printout(" - {}".format(member))
        if serviceNames:
            self._printout("\nServices:")
            for idx, service in enumerate(serviceNames):
                self._printout(" - {}".format(bytes32_to_str(service)))
        if repositoryNames:
            self._printout("\nRepositories:")
            for idx, repo in enumerate(repositoryNames):
                self._printout(" - {}".format(bytes32_to_str(repo)))

    def create(self):
        org_id = self.args.org_id
        # create unique uuid if org_id haven't been specified manualy
        if (not org_id):
            alphabet = string.ascii_letters + string.digits
            org_id   = ''.join(secrets.choice(alphabet) for i in range(32))

        # Check if Organization already exists
        found = self._getorganizationbyid(org_id)[0]
        if found:
            raise Exception("\nOrganization with id={} already exists!\n".format(org_id))

        members = self.get_members_from_args()
        params = [type_converter("bytes32")(org_id), self.args.org_name, members]
        self._printout("Creating transaction to create organization name={} id={}\n".format(self.args.org_name, org_id))
        self.transact_contract_command("Registry", "createOrganization", params)
        self._printout("id:\n%s"%org_id)

    def delete(self):
        org_id = self.args.org_id
        # Check if Organization exists
        (found,_,org_name,_,_,_,_) = self._getorganizationbyid(org_id)
        self.error_organization_not_found(org_id, found)

        self._printout("Creating transaction to delete organization with name={} id={}".format(org_name, org_id))
        try:
            self.transact_contract_command("Registry", "deleteOrganization", [type_converter("bytes32")(org_id)])
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of organization with id={}\n".format(org_id))
            raise

    def list_services(self):
        org_id = self.args.org_id
        (found, org_service_list) = self.call_contract_command("Registry", "listServicesForOrganization", [type_converter("bytes32")(org_id)])
        self.error_organization_not_found(org_id, found)
        if org_service_list:
            self._printout("\nList of {}'s Services:".format(org_id))
            for idx, org_service in enumerate(org_service_list):
                self._printout("- {}".format(bytes32_to_str(org_service)))
        else:
            self._printout("Organization with id={} exists but has no registered services.".format(org_id))

    def change_name(self):
        org_id = self.args.org_id
        new_org_name = self.args.name
        # Check if Organization exists
        (found, _, org_name, _, _, _, _) = self._getorganizationbyid(org_id)
        self.error_organization_not_found(org_id, found)
    
        if new_org_name == org_name:
            raise Exception("\n{} is already the name of the Organization with id={}!\n".format(new_org_name, org_id))
    
        self._printout("Creating transaction to change organization {}'s name...\n".format(org_id))
        try:
            self.transact_contract_command("Registry", "changeOrganizationName", [type_converter("bytes32")(org_id), new_org_name])
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(org_id))
            raise

    def change_owner(self):
        org_id = self.args.org_id
        # Check if Organization exists
        (found, _, _, owner, _, _, _) = self._getorganizationbyid(org_id)
        self.error_organization_not_found(org_id, found)

        new_owner = self.args.owner
        if not web3.eth.is_checksum_address(new_owner):
            raise Exception("New owner account %s is not a valid Ethereum checksum address"%new_owner)

        if new_owner.lower() == owner.lower():
            raise Exception("\n{} is the owner of Organization with id={}!\n".format(new_owner, org_id))

        self._printout("Creating transaction to change organization {}'s owner...\n".format(org_id))
        try:
            self.transact_contract_command("Registry", "changeOrganizationOwner", [type_converter("bytes32")(org_id), self.args.owner])
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(org_id))
            raise

    def add_members(self):
        org_id = self.args.org_id
        # Check if Organization exists and member is not part of it
        (found, _, _, _, members, _, _) = self._getorganizationbyid(org_id)
        self.error_organization_not_found(org_id, found)

        members = [member.lower() for member in members]
        add_members = []
        for add_member in self.get_members_from_args():
            if add_member.lower() in members:
                self._printout("{} is already a member of organization {}".format(add_member, org_id))
            else:
                add_members.append(add_member)

        if not add_members:
            self._printout("No member was added to {}!\n".format(org_id))
            return

        params = [type_converter("bytes32")(org_id), add_members]
        self._printout("Creating transaction to add {} members into organization {}...\n".format(len(add_members), org_id))
        try:
            self.transact_contract_command("Registry", "addOrganizationMembers", params)
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(org_id))
            raise

    def rem_members(self):
        org_id = self.args.org_id
        # Check if Organization exists and member is part of it
        (found, _, _, _, members, _, _) = self._getorganizationbyid(org_id)
        self.error_organization_not_found(org_id, found)

        members = [member.lower() for member in members]
        rem_members = []
        for rem_member in self.get_members_from_args():
            if rem_member.lower() not in members:
                self._printout("{} is not a member of organization {}".format(rem_member, org_id))
            else:
                rem_members.append(rem_member)

        if not rem_members:
            self._printout("No member was removed from {}!\n".format(org_id))
            return

        params = [type_converter("bytes32")(org_id), rem_members]
        self._printout("Creating transaction to remove {} members from organization with id={}...\n".format(len(rem_members), org_id))
        try:
            self.transact_contract_command("Registry", "removeOrganizationMembers", params)
        except Exception as e:
            self._printerr("\nTransaction error!\nHINT: Check if you are the owner of {}\n".format(org_id))
            raise

    def list_my(self):
        """ Find organization that has the current identity as the owner or as the member """
        org_list = self.call_contract_command("Registry", "listOrganizations", [])

        rez_owner  = []
        rez_member = []
        for idx, org_id in enumerate(org_list):
            (found, org_id, org_name, owner, members, serviceNames, repositoryNames) = self.call_contract_command("Registry", "getOrganizationById", [org_id])
            if (not found):
                raise Exception("Organization was removed during this call. Please retry.");
            if self.ident.address == owner:
                rez_owner.append((org_name, bytes32_to_str(org_id)))

            if self.ident.address in members:
                rez_member.append((org_name, bytes32_to_str(org_id)))

        if (rez_owner):
            self._printout("# Organizations you are the owner of")
            self._printout("# OrgName OrgId")
            for n,i in rez_owner:
                self._printout("%s   %s"%(n,i))

        if (rez_member):
            self._printout("# Organizations you are the member of")
            self._printout("# OrgName OrgId")
            for n,i in rez_member:
                self._printout("%s   %s"%(n,i))
