import argparse
import os
import re
import sys
from pathlib import Path

from snet_cli.commands import IdentityCommand, SessionCommand, NetworkCommand, ContractCommand, OrganizationCommand, VersionCommand
from snet_cli.identity import get_identity_types
from snet_cli.utils import type_converter, get_contract_def
from snet_cli.mpe_client_command  import MPEClientCommand
from snet_cli.mpe_service_command import MPEServiceCommand
from snet_cli.utils_agi2cogs import stragi2cogs
from snet_cli.config import get_session_keys, get_session_network_keys_removable

class CustomParser(argparse.ArgumentParser):
    def __init__(self, default_choice=None, *args, **kwargs):
        self.default_choice = default_choice
        super().__init__(*args, **kwargs)

    def error(self, message):
        sys.stderr.write("error: {}\n\n".format(message))
        self.print_help(sys.stderr)
        sys.exit(2)

    def _parse_known_args(self, arg_strings, *args, **kwargs):
        if self.default_choice and not len(list(filter(lambda option: option in arg_strings, {'-h', '--help'}))):
            for action in list(filter(
                lambda subparser_action: isinstance(subparser_action, argparse._SubParsersAction),
                self._subparsers._actions
            )):
                if not len(list(filter(lambda arg: arg in action._name_parser_map.keys(), arg_strings))):
                    arg_strings = [self.default_choice] + arg_strings

        return super()._parse_known_args(
            arg_strings, *args, **kwargs
        )


def get_root_parser(config):
    parser = CustomParser(prog="snet", description="SingularityNET CLI")
    parser.add_argument("--print-traceback", action='store_true', help="Do not catch last exception and print full TraceBack")
    add_root_options(parser, config)

    return parser


def add_root_options(parser, config):
    subparsers = parser.add_subparsers(title="snet commands", metavar="COMMAND")
    subparsers.required = True

    version_p = subparsers.add_parser("version", help="Show version and exit")
    add_version_options(version_p)

    identity_p = subparsers.add_parser("identity", help="Manage identities")
    add_identity_options(identity_p, config)

    network_p = subparsers.add_parser("network", help="Manage networks")
    add_network_options(network_p, config)

    session_p = subparsers.add_parser("session", help="View session state")
    add_session_options(session_p)

    set_p = subparsers.add_parser("set", help="Set session keys")
    add_set_options(set_p)

    unset_p = subparsers.add_parser("unset", help="Unset session keys")
    add_unset_options(unset_p)

    contract_p = subparsers.add_parser("contract", help="Interact with contracts at a low level")
    add_contract_options(contract_p)

    organization_p = subparsers.add_parser("organization", help="Interact with SingularityNET Organizations")
    add_organization_options(organization_p)

    mpe_client_p = subparsers.add_parser("client", help="Interact with SingularityNET services")
    add_mpe_client_options(mpe_client_p)

    mpe_server_p = subparsers.add_parser("service", help="Create, publish, register, and update SingularityNET services")
    add_mpe_service_options(mpe_server_p)


def add_version_options(parser):
    parser.set_defaults(cmd=VersionCommand)
    parser.set_defaults(fn="show")


def add_identity_options(parser, config):
    parser.set_defaults(cmd=IdentityCommand)

    subparsers = parser.add_subparsers(title="actions", metavar="ACTION")
    subparsers.required = True

    p = subparsers.add_parser("list", help="List of identies")
    p.set_defaults(fn="list")

    p = subparsers.add_parser("create", help="Create a new identity")
    p.set_defaults(fn="create")
    p.add_argument("identity_name", help="name of identity to create", metavar="IDENTITY_NAME")
    p.add_argument("identity_type", choices=get_identity_types(),
                   help="type of identity to create from {}".format(get_identity_types()),
                   metavar="IDENTITY_TYPE")
    p.add_argument("--mnemonic", help="bip39 mnemonic for 'mnemonic' identity_type")
    p.add_argument("--private-key", help="hex-encoded private key for 'key' identity_type")
    p.add_argument("--network", help="network this identity will be bind to (obligatory for 'rpc' identity_type, optional for others)")
    p.add_argument("--wallet-index", type=int, default=0, help="default wallet index for this account (default is 0)")

    p = subparsers.add_parser("delete", help="Delete an identity")
    p.set_defaults(fn="delete")

    identity_names = config.get_all_identies_names()

    p.add_argument("identity_name", choices=identity_names,
                   help="name of identity to delete from {}".format(identity_names), metavar="IDENTITY_NAME")

    for identity_name in identity_names:
        p = subparsers.add_parser(identity_name, help="Switch to {} identity".format(identity_name))
        p.set_defaults(identity_name=identity_name)
        p.set_defaults(fn="set")


def add_network_options(parser, config):
    parser.set_defaults(cmd=NetworkCommand)

    subparsers = parser.add_subparsers(title="networks", metavar="NETWORK")
    subparsers.required = True

    p = subparsers.add_parser("list", help="List of networks")
    p.set_defaults(fn="list")

    p = subparsers.add_parser("create", help="Create a new network")
    p.set_defaults(fn="create")
    p.add_argument("network_name", help="name of network to create")
    p.add_argument("eth_rpc_endpoint", help="ethereum rpc endpoint")
    p.add_argument("--default_gas_price", default=1000000000, type=int, help="default gas price for this network (in wei), default is 1000000000")


    network_names = config.get_all_networks_names()

    for network_name in network_names:
        p = subparsers.add_parser(network_name, help="Switch to {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        p.set_defaults(fn="set")


def add_session_options(parser):
    parser.set_defaults(cmd=SessionCommand)
    parser.set_defaults(fn="show")


def add_set_options(parser):
    parser.set_defaults(cmd=SessionCommand)
    parser.set_defaults(fn="set")
    parser.add_argument("key", choices=get_session_keys(), help="session key to set from {}".format(get_session_keys()),
                        metavar="KEY")
    parser.add_argument("value", help="desired value of session key", metavar="VALUE")


def add_unset_options(parser):
    parser.set_defaults(cmd=SessionCommand)
    parser.set_defaults(fn="unset")
    parser.add_argument("key", choices=get_session_network_keys_removable(),
                        help="session key to unset from {}".format(get_session_network_keys_removable()), metavar="KEY")


def add_contract_options(parser):
    parser.set_defaults(cmd=ContractCommand)

    subparsers = parser.add_subparsers(title="contracts", metavar="CONTRACT")
    subparsers.required = True

    for path in Path(__file__).absolute().parent.joinpath("resources", "contracts", "abi").glob("*json"):
        contract_name = re.search(r"([^.]*)\.json", os.path.basename(path)).group(1)
        contract_p = subparsers.add_parser(contract_name, help="{} contract".format(contract_name))
        add_contract_function_options(contract_p, contract_name)


def _add_organization_arguments(parser):
    add_transaction_arguments(parser)
    add_contract_identity_arguments(parser, [("registry", "registry_at")])


def add_organization_options(parser):
    parser.set_defaults(cmd=OrganizationCommand)

    subparsers = parser.add_subparsers(title="organization commands", metavar="COMMAND")
    subparsers.required = True

    p = subparsers.add_parser("list", help="List Organizations")
    p.set_defaults(fn="list")
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    p = subparsers.add_parser("info", help="Organization's Informations")
    p.set_defaults(fn="info")
    p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    org_create_p = subparsers.add_parser("create", help="Create an Organization")
    org_create_p.set_defaults(fn="create")
    org_create_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_create_p.add_argument("--members",
                              help="List of members to be added to the organization",
                              metavar="ORG_MEMBERS[]")
    _add_organization_arguments(org_create_p)

    org_delete_p = subparsers.add_parser("delete", help="Delete an Organization")
    org_delete_p.set_defaults(fn="delete")
    org_delete_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    _add_organization_arguments(org_delete_p)

    p = subparsers.add_parser("list-services", help="List Organization's services")
    p.set_defaults(fn="list_services")
    p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    org_change_owner_p = subparsers.add_parser("change-owner", help="Change Organization's owner")
    org_change_owner_p.set_defaults(fn="change_owner")
    org_change_owner_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_change_owner_p.add_argument("owner", help="Address of the new Organization's owner", metavar="OWNER_ADDRESS")
    _add_organization_arguments(org_change_owner_p)

    org_add_members_p = subparsers.add_parser("add-members", help="Add members to Organization")
    org_add_members_p.set_defaults(fn="add_members")
    org_add_members_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_add_members_p.add_argument("members",
                                   help="List of members to be added to the organization",
                                   metavar="ORG_MEMBERS[]")
    _add_organization_arguments(org_add_members_p)

    org_rm_members_p = subparsers.add_parser("rem-members", help="Remove members from Organization")
    org_rm_members_p.set_defaults(fn="rem_members")
    org_rm_members_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_rm_members_p.add_argument("members",
                                  help="List of members to be removed from the organization",
                                  metavar="ORG_MEMBERS[]")
    _add_organization_arguments(org_rm_members_p)


def add_contract_function_options(parser, contract_name):
    add_contract_identity_arguments(parser)

    contract_def = get_contract_def(contract_name)
    parser.set_defaults(contract_def=contract_def)
    parser.set_defaults(contract_name=contract_name)

    fns = []
    for fn in filter(lambda e: e["type"] == "function", contract_def["abi"]):
        fns.append({
            "name": fn["name"],
            "named_inputs": [(i["name"], i["type"]) for i in fn["inputs"] if i["name"] != ""],
            "positional_inputs": [i["type"] for i in fn["inputs"] if i["name"] == ""]
        })

    if len(fns) > 0:
        subparsers = parser.add_subparsers(title="{} functions".format(contract_name), metavar="FUNCTION")
        subparsers.required = True

        for fn in fns:
            fn_p = subparsers.add_parser(fn["name"], help="{} function".format(fn["name"]))
            fn_p.set_defaults(fn="call")
            fn_p.set_defaults(contract_function=fn["name"])
            for i in fn["positional_inputs"]:
                fn_p.add_argument(i, action=AppendPositionalAction, type=type_converter(i), metavar=i.upper())
            for i in fn["named_inputs"]:
                fn_p.add_argument("contract_named_input_{}".format(i[0]), type=type_converter(i[1]),
                                  metavar="{}_{}".format(i[0].lstrip("_"), i[1].upper()))
            fn_p.add_argument("--transact", action="store_const", const="transact", dest="fn",
                              help="invoke contract function as transaction")
            add_transaction_arguments(fn_p)


def add_contract_identity_arguments(parser, names_and_destinations=(("", "at"),)):
    identity_g = parser.add_argument_group(title="contract identity arguments")
    for (name, destination) in names_and_destinations:
        if name != "":
            arg_name = "{}-".format(name)
            metavar_name = "{}_".format(name.replace("-", "_"))
        else:
            arg_name = name
            metavar_name = name
        h = "{} contract address".format(name)
        if destination != "at":
            h += " (defaults to session.current_{})".format(destination)
        identity_g.add_argument("--{}at".format(arg_name), dest=destination, type=type_converter("address"),
                                metavar="{}ADDRESS".format(metavar_name.upper()),
                                help=h)


def add_eth_call_arguments(parser):
    p= parser.add_argument_group(title="optional call arguments")
    p.add_argument("--wallet-index", type=int,
                   help="wallet index of account to use for calling (defaults to session.identity.default_wallet_index)")


def add_transaction_arguments(parser):
    transaction_g = parser.add_argument_group(title="transaction arguments")
    transaction_g.add_argument("--gas-price", type=int,
                               help="ethereum gas price for transaction (defaults to session.default_gas_price)")
    transaction_g.add_argument("--wallet-index", type=int,
                               help="wallet index of account to use for signing (defaults to session.identity.default_wallet_index)")
    transaction_g.add_argument("--yes", "-y", action="store_true",
                               help="skip interactive confirmation of transaction payload", default=False)
    g = transaction_g.add_mutually_exclusive_group()
    g.add_argument("--verbose", "-v", action="store_true", help="verbose transaction printing", default=False)
    g.add_argument("--quiet", "-q", action="store_true", help="quiet transaction printing", default=False)


class AppendPositionalAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        positional_inputs = getattr(namespace, "contract_positional_inputs", None)
        if positional_inputs is None:
            setattr(namespace, "contract_positional_inputs", [])
        getattr(namespace, "contract_positional_inputs").append(values)
        delattr(namespace, self.dest)


def add_p_mpe_address_opt(p):
    p.add_argument("--multipartyescrow-at", "--mpe", default=None,  help="address of MultiPartyEscrow contract, if not specified we read address from \"networks\"")


def add_p_metadata_file_opt(p):
    p.add_argument("--metadata_file", default="service_metadata.json", help="Service metadata json file (default service_metadata.json)")


def add_p_service_in_registry(p):
    p.add_argument("--registry-at", "--registry", default=None, help="address of Registry contract, if not specified we read address from \"networks\"")
    p.add_argument("organization", help="Name of organization")
    p.add_argument("service",      help="Name of service")


def add_mpe_client_options(parser):
    parser.set_defaults(cmd=MPEClientCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True

    def add_p_channel_id(p):
        # int is ok here because in python3 int is unlimited
        p.add_argument("channel_id", type=int, help="channel_id")
    def add_p_endpoint(p):        
        p.add_argument("endpoint",             help="service endpoint")
    def add_p_full_service_for_call(p):
        add_p_endpoint(p)
        p.add_argument("--service", default=None, help="name of protobuf service to call. It should be specified in case of method name conflict.")
        p.add_argument("method",                  help="target service's method name to call")
        p.add_argument("params", nargs='?',       help="json-serialized parameters object or path containing "
                                                "json-serialized parameters object (leave emtpy to read from stdin)")        
    def add_p_full_message(p):
        add_p_mpe_address_opt(p)
        add_p_channel_id(p)
        p.add_argument("nonce",      type=int, help="nonce of the channel")
        p.add_argument("amount",     type=int, help="amount")

    def add_p_snt_address_opt(p):
        p.add_argument("--singularitynettoken-at", "--snt", default=None,  help="address of SingularityNetToken contract, if not specified we read address from \"networks\"")

    def add_p_open_channel_basic(p):
        p.add_argument("amount",         type=stragi2cogs, help="amount of AGI tokens to put in the new channel")
        p.add_argument("expiration",     type=int, help="expiration time (in blocks) for the new channel (one block ~ 15 seconds)")
        p.add_argument("--group_name", default=None, help="name of payment group for which we want to open the channel. Parameter should be specified only for services with several payment groups")
        add_p_mpe_address_opt(p)
        add_transaction_arguments(p)

    p = subparsers.add_parser("account", help="print the currect ETH account")
    p.set_defaults(fn="print_account")
    add_eth_call_arguments(p)

    p = subparsers.add_parser("balance", help="print balance of AGI tokens and balance of MPE wallet")
    p.set_defaults(fn="print_agi_and_mpe_balances")
    p.add_argument("--account", default=None, help="Account to print balance for (default is the current identity)")
    add_p_snt_address_opt(p)
    add_p_mpe_address_opt(p)
    add_eth_call_arguments(p)

    p = subparsers.add_parser("deposit", help="deposit AGI tokens to MPE wallet")
    p.set_defaults(fn="deposit_to_mpe")
    p.add_argument("amount",  type=stragi2cogs, help="amount of AGI tokens to deposit in MPE wallet")
    add_p_snt_address_opt(p)
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("withdraw", help="withdraw AGI tokens from MPE wallet")
    p.set_defaults(fn="withdraw_from_mpe")
    p.add_argument("amount",  type=stragi2cogs, help="amount of AGI tokens to withdraw from MPE wallet")
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("transfer", help="transfer AGI tokens inside MPE wallet")
    p.set_defaults(fn="transfer_in_mpe")
    p.add_argument("receiver", help="address of the receiver")
    p.add_argument("amount",   type=stragi2cogs, help="amount of AGI tokens to be transfered to another account inside MPE wallet")
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("init_channel_metadata", help="Initialize channel using service metadata")
    p.set_defaults(fn="init_channel_from_metadata")
    add_p_metadata_file_opt(p)
    add_p_mpe_address_opt(p)
    add_p_channel_id(p)

    p = subparsers.add_parser("init_channel_registry", help="Initialize channel taking service metadata from Registry")
    p.set_defaults(fn="init_channel_from_registry")
    add_p_service_in_registry(p)
    add_p_mpe_address_opt(p)
    add_p_channel_id(p)

    p = subparsers.add_parser("open_init_channel_metadata", help="Open and initilize channel using service metadata")
    p.set_defaults(fn="open_init_channel_from_metadata")
    add_p_open_channel_basic(p)
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("open_init_channel_registry", help="Open and initilize channel using metadata from Registry")
    p.set_defaults(fn="open_init_channel_from_registry")
    add_p_service_in_registry(p)
    add_p_open_channel_basic(p)
    
    p = subparsers.add_parser("channel_claim_timeout", help="Claim timeout of the channel")
    p.set_defaults(fn="channel_claim_timeout")
    add_p_channel_id(p)
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("channel_extend_add", help="Set new exporation for the channel and add funds")
    p.set_defaults(fn="channel_extend_and_add_funds")
    add_p_channel_id(p)
    expiration_amount_g = p.add_argument_group(title="Expiration and amount")
    expiration_amount_g.add_argument("--expiration", type=int,         required=True, help="New expiration for the channel (should be bigger then old one)")
    expiration_amount_g.add_argument("--amount",     type=stragi2cogs, required=True, help="Amount of AGI tokens to add to the channel")
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("call", help="call server in stateless manner. We ask state of the channel from the server. Channel should be already initialized.")
    p.set_defaults(fn="call_server_statelessly")
    add_p_channel_id(p)
    p.add_argument("price",     type=stragi2cogs, help="price for this call in AGI tokens")
    add_p_full_service_for_call(p)                                                
    add_p_mpe_address_opt(p)
    
    p = subparsers.add_parser("call_lowlevel", help="Low level function for calling the server. Channel should be already initialized.")
    p.set_defaults(fn="call_server_lowlevel")
    add_p_full_message(p)
    add_p_full_service_for_call(p)
    
    p = subparsers.add_parser("block_number", help="Print the last ethereum block number")
    p.set_defaults(fn="print_block_number")

    p = subparsers.add_parser("print_all_channels", help="Print all channels related to the current identity. It may take a long time.")
    p.set_defaults(fn="print_all_channels_my")
    add_p_mpe_address_opt(p)
    p.add_argument("--from_block", type=int, default=0, help="Start searching from this block")

    p = subparsers.add_parser("print_initialized_channels", help="Print initialized channels related to the current identity.")
    p.set_defaults(fn="print_initialized_channels_my")
    add_p_mpe_address_opt(p)

    p = subparsers.add_parser("get_channel_state", help="Get channel state in stateless manner")
    p.set_defaults(fn="print_channel_state_statelessly")
    add_p_mpe_address_opt(p)
    add_p_channel_id(p)
    add_p_endpoint(p)


def add_mpe_service_options(parser):
    parser.set_defaults(cmd=MPEServiceCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True
    
    def add_p_protodir(p):
        p.add_argument("protodir",     help="Directory which contains protobuf files")

    p = subparsers.add_parser("metadata_init", help="Init metadata file with providing protobuf directory (which we publish in IPFS) and display_name (optionally encoding, service_type and payment_expiration_threshold)")
    p.set_defaults(fn="publish_proto_metadata_init")
    add_p_protodir(p)
    add_p_metadata_file_opt(p)
    add_p_mpe_address_opt(p)
    p.add_argument("display_name", help="Service display name")
    p.add_argument("payment_address", help="payment_address for the first payment group")
    p.add_argument("--group_name", default="default_group", help="name of the first payment group")
    p.add_argument("--encoding", default = "proto", choices=['proto', 'json'], help="Service encoding")
    p.add_argument("--service_type", default = "grpc", choices=['grpc', 'jsonrpc', 'process'], help="Service type")
    p.add_argument("--payment_expiration_threshold", type=int, default = 40320, help="Service expiration threshold in blocks (default is 40320 ~ one week with 15s/block)")

    p = subparsers.add_parser("metadata_set_fixed_price", help="Set pricing model as fixed price for all methods")
    p.set_defaults(fn="metadata_set_fixed_price")
    p.add_argument("price", type = stragi2cogs, help="set fixed price in AGI token for all methods")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata_add_group", help="Add new group of replicas")
    p.set_defaults(fn="metadata_add_group")
    add_p_metadata_file_opt(p)
    p.add_argument("group_name", help="name of the new payment group")
    p.add_argument("payment_address", help="payment_address for this group")
 
    p = subparsers.add_parser("metadata_add_endpoints", help="Add endpoints to the groups")
    p.set_defaults(fn="metadata_add_endpoints")
    p.add_argument("endpoints", nargs="+",  help="endpoints")
    p.add_argument("--group_name", default=None, help="name of the payment group to which we want to add endpoints. Parameter should be specified in case of several payment groups")
    add_p_metadata_file_opt(p)
 
    p = subparsers.add_parser("publish_in_ipfs", help="Publish metadata only in IPFS, without publising in Registry")
    p.set_defaults(fn="publish_metadata_in_ipfs")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("publish", help="Publish service with given metadata")
    p.set_defaults(fn="publish_service_with_metadata")
    add_p_service_in_registry(p)
    add_p_metadata_file_opt(p)
    p.add_argument("--tags", nargs="*", default=[], help="tags for service")
    add_transaction_arguments(p)

    p = subparsers.add_parser("update_metadata", help="Publish metadata in IPFS and update existed service")
    p.set_defaults(fn="publish_metadata_in_ipfs_and_update_registration")
    add_p_service_in_registry(p)
    add_p_metadata_file_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("update_add_tags", help="Add tags to existed service registration")
    p.set_defaults(fn="update_registration_add_tags")
    add_p_service_in_registry(p)
    p.add_argument("tags", nargs="+", default=[], help="tags which will be add")
    add_transaction_arguments(p)

    p = subparsers.add_parser("update_remove_tags", help="Remove tags from existed service registration")
    p.set_defaults(fn="update_registration_remove_tags")
    add_p_service_in_registry(p)
    p.add_argument("tags", nargs="+", default=[], help="tags which will be removed")
    add_transaction_arguments(p)

    p = subparsers.add_parser("print_metadata", help="Print service metadata from registry")
    p.set_defaults(fn="print_service_metadata_from_registry")
    add_p_service_in_registry(p)

    p = subparsers.add_parser("print_tags", help="Print tags for given service from registry")
    p.set_defaults(fn="print_service_tags_from_registry")
    add_p_service_in_registry(p)

    p = subparsers.add_parser("delete", help="Delete service registration from registry")
    p.set_defaults(fn="delete_service_registration")
    add_p_service_in_registry(p)
    add_transaction_arguments(p)
