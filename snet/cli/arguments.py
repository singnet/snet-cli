import argparse
import os
import re
import sys

from snet.contracts import get_all_abi_contract_files, get_contract_def

from snet.cli.commands.commands import ContractCommand, IdentityCommand, NetworkCommand, OrganizationCommand, SessionSetCommand, SessionShowCommand, VersionCommand
from snet.cli.commands.mpe_account import MPEAccountCommand
from snet.cli.commands.mpe_channel import MPEChannelCommand
from snet.cli.commands.mpe_client import MPEClientCommand
from snet.cli.commands.mpe_service import MPEServiceCommand
from snet.cli.commands.mpe_treasurer import MPETreasurerCommand
from snet.cli.commands.sdk_command import SDKCommand
from snet.cli.config import Config, get_session_keys, get_session_network_keys_removable
from snet.cli.identity import get_identity_types
from snet.cli.utils.token2cogs import strtoken2cogs
from snet.cli.utils.utils import type_converter


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
                    lambda subparser_action: isinstance(
                        subparser_action, argparse._SubParsersAction),
                    self._subparsers._actions
            )):
                if not len(list(filter(lambda arg: arg in action._name_parser_map.keys(), arg_strings))):
                    arg_strings = [self.default_choice] + arg_strings

        return super()._parse_known_args(
            arg_strings, *args, **kwargs
        )


def get_parser():
    return get_root_parser(Config())


def get_root_parser(config):
    parser = CustomParser(prog="snet", description="SingularityNET CLI")
    parser.add_argument("--print-traceback",
                        action='store_true',
                        help="Do not catch last exception and print full TraceBack")
    add_root_options(parser, config)

    return parser


def add_root_options(parser, config):
    subparsers = parser.add_subparsers(
        title="snet commands", metavar="COMMAND")
    subparsers.required = True

    p = subparsers.add_parser("account", help="ASI(FET) account")
    add_mpe_account_options(p)

    p = subparsers.add_parser("channel", help="Interact with SingularityNET payment channels")
    add_mpe_channel_options(p)

    mpe_client_p = subparsers.add_parser("client", help="Interact with SingularityNET services")
    add_mpe_client_options(mpe_client_p)

    contract_p = subparsers.add_parser("contract", help="Interact with contracts at a low level")
    add_contract_options(contract_p)

    identity_p = subparsers.add_parser("identity", help="Manage identities")
    add_identity_options(identity_p, config)

    network_p = subparsers.add_parser("network", help="Manage networks")
    add_network_options(network_p, config)

    organization_p = subparsers.add_parser("organization", help="Interact with SingularityNET Organizations")
    add_organization_options(organization_p)

    sdk_p = subparsers.add_parser(
        "sdk",
        help="Generate client libraries to call SingularityNET services using your language of choice")
    add_sdk_options(sdk_p)

    mpe_server_p = subparsers.add_parser(
        "service",
        help="Create, publish, register, and update SingularityNET services")
    add_mpe_service_options(mpe_server_p)

    session_p = subparsers.add_parser("session", help="View session state")
    add_session_options(session_p)

    set_p = subparsers.add_parser("set", help="Set session keys")
    add_set_options(set_p)

    p = subparsers.add_parser("treasurer", help="Treasurer logic")
    add_mpe_treasurer_options(p)

    unset_p = subparsers.add_parser("unset", help="Unset session keys")
    add_unset_options(unset_p)

    version_p = subparsers.add_parser("version", help="Show version and exit")
    add_version_options(version_p)


def add_version_options(parser):
    parser.set_defaults(cmd=VersionCommand)
    parser.set_defaults(fn="show")


def add_identity_options(parser, config):
    parser.set_defaults(cmd=IdentityCommand)

    subparsers = parser.add_subparsers(title="actions", metavar="ACTION")
    subparsers.required = True

    p = subparsers.add_parser("list",
                              help="List of identities")
    p.set_defaults(fn="list")

    p = subparsers.add_parser("create",
                              help="Create a new identity. For 'mnemonic' and 'key' identity_type, "
                                   "secret encryption is enabled by default.")
    p.set_defaults(fn="create")
    p.add_argument("identity_name",
                   help="Name of identity to create",
                   metavar="IDENTITY_NAME")
    p.add_argument("identity_type",
                   choices=get_identity_types(),
                   help="Type of identity to create from {}".format(
                       get_identity_types()),
                   metavar="IDENTITY_TYPE")
    p.add_argument("-de", "--do-not-encrypt",
                   default=False,
                   action="store_true",
                   help="Do not encrypt the identity's private key or mnemonic. For 'key' and 'mnemonic' identity_type.")
    p.add_argument("--mnemonic",
                   help="BIP39 mnemonic for 'mnemonic' identity_type")
    p.add_argument("--private-key",
                   help="Hex-encoded private key for 'key' identity_type")
    p.add_argument("--keystore-path",
                   help="Path of the JSON encrypted file for 'keystore' identity_type")
    p.add_argument("--network",
                   help="Network this identity will be bind to (obligatory for 'rpc' identity_type, optional for others)")
    p.add_argument("--wallet-index",
                   type=int,
                   default=0,
                   help="Default wallet index for this account (default is 0)")

    p = subparsers.add_parser("delete",
                              help="Delete an identity")
    p.set_defaults(fn="delete")

    identity_names = config.get_all_identities_names()
    p.add_argument("identity_name",
                   choices=identity_names,
                   help="Name of identity to delete from {}".format(
                       identity_names),
                   metavar="IDENTITY_NAME")

    for identity_name in identity_names:
        p = subparsers.add_parser(identity_name,
                                  help="Switch to {} identity".format(identity_name))
        p.set_defaults(identity_name=identity_name)
        p.set_defaults(fn="set")


def add_network_options(parser, config):
    parser.set_defaults(cmd=NetworkCommand)

    subparsers = parser.add_subparsers(title="networks", metavar="NETWORK")
    subparsers.required = True

    p = subparsers.add_parser("list",
                              help="List of networks")
    p.set_defaults(fn="list")

    p = subparsers.add_parser("create",
                              help="Create a new network")
    p.set_defaults(fn="create")
    p.add_argument("network_name",
                   help="Name of network to create")
    p.add_argument("eth_rpc_endpoint",
                   help="Ethereum rpc endpoint")
    p.add_argument("--skip-check",
                   action="store_true",
                   help="Skip check that eth_rpc_endpoint is valid")

    network_names = config.get_all_networks_names()
    for network_name in network_names:
        p = subparsers.add_parser(
            network_name, help="Switch to {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        p.set_defaults(fn="set")


def add_session_options(parser):
    parser.set_defaults(cmd=SessionShowCommand)
    parser.set_defaults(fn="show")


def add_set_options(parser):
    parser.set_defaults(cmd=SessionSetCommand)
    parser.set_defaults(fn="set")
    parser.add_argument("key",
                        choices=get_session_keys(),
                        help="Session key to set from {}".format(
                            get_session_keys()),
                        metavar="KEY")
    parser.add_argument("value",
                        help="Desired value of session key",
                        metavar="VALUE")


def add_unset_options(parser):
    parser.set_defaults(cmd=SessionSetCommand)
    parser.set_defaults(fn="unset")
    parser.add_argument("key",
                        choices=get_session_network_keys_removable(),
                        help="Session key to unset from {}".format(
                            get_session_network_keys_removable()),
                        metavar="KEY")


def add_contract_options(parser):
    parser.set_defaults(cmd=ContractCommand)

    subparsers = parser.add_subparsers(title="contracts", metavar="CONTRACT")
    subparsers.required = True

    contracts = get_all_abi_contract_files()
    for path in contracts:
        if "MultiPartyEscrow" in str(path) or "Registry" in str(path) or "FetchToken" in str(path):
            contract_name = re.search(
                r"([^.]*)\.json", os.path.basename(path)).group(1)
            contract_p = subparsers.add_parser(
                contract_name, help="{} contract".format(contract_name))
            add_contract_function_options(contract_p, contract_name)


def add_organization_arguments(parser):
    add_transaction_arguments(parser)
    add_contract_identity_arguments(parser, [("registry", "registry_at")])


def add_p_org_id(p):
    p.add_argument("org_id",
                   help="Id of the Organization",
                   metavar="ORG_ID")


def add_metadatafile_argument_for_org(p):
    p.add_argument("--metadata-file",
                   default="organization_metadata.json",
                   help="Organization metadata json file (default organization_metadata.json)")


def add_p_storage_param(_p):
    _p.add_argument(
        "--storage",
        default="ipfs",
        choices=['ipfs', 'filecoin'],
        help="Choose storage for uploading metadata/protobuf file (defaults to 'ipfs')",
    )


def add_organization_options(parser):
    parser.set_defaults(cmd=OrganizationCommand)

    subparsers = parser.add_subparsers(
        title="Organization commands", metavar="COMMAND")
    subparsers.required = True

    p = subparsers.add_parser("metadata-init", help="Initialize metadata for organization")
    p.set_defaults(fn="initialize_metadata")
    p.add_argument("org_name", help="Organization name", metavar="ORG_NAME")
    p.add_argument("org_id", default=None, help="Unique organization Id", metavar="ORG_ID")
    p.add_argument("org_type", help="organization type based on creator of organization whether it is individual or business/organization "
                                    "[ individual | organization ]",
                   choices=["individual", "organization"], metavar="ORG_TYPE")
    add_p_registry_address_opt(p)
    add_metadatafile_argument_for_org(p)

    p = subparsers.add_parser("print-metadata", help="Print metadata for given organization")
    p.set_defaults(fn="print_metadata")
    p.add_argument("org_id", help="Organization Id")

    p = subparsers.add_parser("add-group", help="Add group to organization")
    p.set_defaults(fn="add_group")
    p.add_argument("group_name", help="Group Name ")
    p.add_argument("payment_address", help="Payment address")
    p.add_argument("endpoints", nargs='*', help="Endpoints for the first group")
    p.add_argument("--payment-expiration-threshold", type=int, default=100, help="Payment Expiration threshold")
    p.add_argument("--payment-channel-storage-type", default="etcd", help="Storage channel for payment")
    p.add_argument("--payment-channel-connection-timeout", default="7s", help="Payment channel connection timeout ")
    p.add_argument("--payment-channel-request-timeout", default="5s", help="Payment channel request timeout")
    add_metadatafile_argument_for_org(p)
    add_p_registry_address_opt(p)

    p = subparsers.add_parser("update-group", help="Update group of organization ")
    p.set_defaults(fn="update_group")
    p.add_argument("group_id", help="Group Id")
    p.add_argument("--payment-address", help="Payment Address")
    p.add_argument("--endpoints", nargs='*', help="Endpoints for the first group")
    p.add_argument("--payment-expiration-threshold", help="Payment Expiration threshold")
    p.add_argument("--payment-channel-storage-type", help="Payment Channel Storage Type")
    p.add_argument("--payment-channel-connection-timeout", help="Payment Channel Connection timeout")
    p.add_argument("--payment-channel-request-timeout", help="Payment channel Request timeout")
    add_metadatafile_argument_for_org(p)
    add_p_registry_address_opt(p)

    # p = subparsers.add_parser("remove-group",
    #                           help="Remove group of organization ")
    # p.set_defaults(fn="remove_group")
    #
    # p.add_argument("group_id",
    #                help="Group Id ")
    # add_metadatafile_argument_for_org(p)
    # add_p_registry_address_opt(p)

    p = subparsers.add_parser("metadata-add-description", help="Add description to metadata")
    p.set_defaults(fn="metadata_add_description")
    p.add_argument("--description", help="description about organization info", metavar="DESCRIPTION")
    p.add_argument("--short-description", help="description about organization info", metavar="SHORT_DESCRIPTION")
    p.add_argument("--url", help="url for organization website", metavar="URL")
    add_p_organization_metadata_file_opt(p)

    p = subparsers.add_parser(
        "metadata-add-assets",
        help="Add assets to metadata, valid asset types are [hero_image]")
    p.set_defaults(fn="metadata_add_asset_to_ipfs")
    p.add_argument("asset_file_path", help="Asset file path", metavar="ASSET_FILE_PATH")
    p.add_argument("asset_type", help="Type of the asset, valid asset types are [hero_image]", metavar="ASSET_TYPE")
    add_p_organization_metadata_file_opt(p)

    p = subparsers.add_parser(
        "metadata-remove-assets",
        help="Remove asset of a given type valid asset types are [hero_image]")
    p.set_defaults(fn="metadata_remove_assets_of_a_given_type")
    p.add_argument("asset_type", help="Type of the asset to be removed, valid asset types are [hero_image]",
                   metavar="ASSET_TYPE")
    add_p_organization_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-all-assets", help="Remove all assets from metadata")
    p.set_defaults(fn="metadata_remove_all_assets")
    add_p_organization_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-add-contact", help="Add contact in organization metadata")
    p.set_defaults(fn="metadata_add_contact")
    p.add_argument("contact_type", help="Contact type of organization")
    p.add_argument("--phone", help="Phone number for contact with country code")
    p.add_argument("--email", help="Email ID for contact")
    add_p_organization_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-all-contacts", help="Remove all contacts")
    p.set_defaults(fn="metadata_remove_all_contacts")
    add_p_organization_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-contacts", help="Remove all contacts")
    p.set_defaults(fn="metadata_remove_contact_by_type")
    p.add_argument("contact_type", help="Contact type of organization", metavar="CONTACT_TYPE")
    add_p_organization_metadata_file_opt(p)

    p = subparsers.add_parser("list", help="List of Organizations Ids")
    p.set_defaults(fn="list")
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    p = subparsers.add_parser("list-org-names", help="List Organizations Names and Ids")
    p.set_defaults(fn="list_org_name")
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    p = subparsers.add_parser(
        "list-my",
        help="Print organization which has the current identity as the owner or as a member")
    p.set_defaults(fn="list_my")
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    p = subparsers.add_parser("list-services", help="List Organization's services")
    p.set_defaults(fn="list_services")
    add_p_org_id(p)
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    p = subparsers.add_parser("info", help="Organization's Information")
    p.set_defaults(fn="info")
    add_p_org_id(p)
    add_contract_identity_arguments(p, [("registry", "registry_at")])
    add_eth_call_arguments(p)

    p = subparsers.add_parser("create", help="Create an Organization")
    p.set_defaults(fn="create")
    p.add_argument("org_id", help="Unique Organization Id", metavar="ORG_ID")
    add_metadatafile_argument_for_org(p)
    p.add_argument("--members", help="List of members to be added to the organization", metavar="ORG_MEMBERS[]")
    add_organization_arguments(p)
    add_p_storage_param(p)

    p = subparsers.add_parser("update-metadata", help="Update metadata for an Organization")
    p.add_argument("org_id", help="Unique Organization Id", metavar="ORG_ID")
    p.set_defaults(fn="update_metadata")
    add_metadatafile_argument_for_org(p)
    p.add_argument(
        "--members",
        help="List of members to be added to the organization",
        metavar="ORG_MEMBERS[]")
    add_organization_arguments(p)
    add_p_storage_param(p)

    p = subparsers.add_parser("change-owner", help="Change Organization's owner")
    p.set_defaults(fn="change_owner")
    add_p_org_id(p)
    p.add_argument("owner", help="Address of the new Organization's owner", metavar="OWNER_ADDRESS")
    add_organization_arguments(p)

    p = subparsers.add_parser("add-members", help="Add members to Organization")
    p.set_defaults(fn="add_members")
    add_p_org_id(p)
    p.add_argument("members", help="List of members to be added to the organization", metavar="ORG_MEMBERS[]")
    add_organization_arguments(p)

    p = subparsers.add_parser("rem-members", help="Remove members from Organization")
    p.set_defaults(fn="rem_members")
    add_p_org_id(p)
    p.add_argument("members", help="List of members to be removed from the organization", metavar="ORG_MEMBERS[]")
    add_organization_arguments(p)

    p = subparsers.add_parser("delete", help="Delete an Organization")
    p.set_defaults(fn="delete")
    add_p_org_id(p)
    add_organization_arguments(p)

    p = subparsers.add_parser("validate-metadata",
                              help="Validates if created metadata is consistent")
    p.set_defaults(fn="metadata_validate")
    add_metadatafile_argument_for_org(p)


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
            "positional_inputs": [i["type"] for i in fn["inputs"] if i["name"] == ""],
            "stateMutability": fn["stateMutability"]
        })

    if len(fns) > 0:
        subparsers = parser.add_subparsers(
            title="{} functions".format(contract_name), metavar="FUNCTION")
        subparsers.required = True

        for fn in fns:
            fn_p = subparsers.add_parser(
                fn["name"], help="{} function".format(fn["name"]))
            if fn["stateMutability"] == "view":
                fn_p.set_defaults(fn="call")
            else:
                fn_p.set_defaults(fn="transact")
            fn_p.set_defaults(contract_function=fn["name"])
            for i in fn["positional_inputs"]:
                fn_p.add_argument(i,
                                  action=AppendPositionalAction,
                                  type=type_converter(i),
                                  metavar=i.upper())
            for i in fn["named_inputs"]:
                fn_p.add_argument("contract_named_input_{}".format(i[0]),
                                  type=type_converter(i[1]),
                                  metavar="{}_{}".format(i[0].lstrip("_"), i[1].upper()))
            if fn["stateMutability"] != "view":
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
        identity_g.add_argument("--{}at".format(arg_name),
                                dest=destination,
                                metavar="{}ADDRESS".format(
                                    metavar_name.upper()),
                                help=h)


def add_eth_call_arguments(parser):
    p = parser.add_argument_group(title="optional call arguments")
    p.add_argument("--wallet-index",
                   type=int,
                   help="Wallet index of account to use for calling (defaults to session.identity.default_wallet_index)")


def add_transaction_arguments(parser):
    transaction_g = parser.add_argument_group(title="transaction arguments")
    transaction_g.add_argument(
        "--wallet-index", type=int,
        help="Wallet index of account to use for signing (defaults to session.identity.default_wallet_index)")
    transaction_g.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip interactive confirmation of transaction payload",
        default=False)
    g = transaction_g.add_mutually_exclusive_group()
    g.add_argument("--quiet", "-q", action="store_true", help="Quiet transaction printing", default=False)
    g.add_argument("--verbose", "-v", action="store_true", help="Verbose transaction printing", default=False)


class AppendPositionalAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        positional_inputs = getattr(
            namespace, "contract_positional_inputs", None)
        if positional_inputs is None:
            setattr(namespace, "contract_positional_inputs", [])
        getattr(namespace, "contract_positional_inputs").append(values)
        delattr(namespace, self.dest)


def add_p_mpe_address_opt(p):
    p.add_argument(
        "--multipartyescrow-at", "--mpe", default=None,
        help="Address of MultiPartyEscrow contract, if not specified we read address from \"networks\"")


def add_p_registry_address_opt(p):
    p.add_argument(
        "--registry-at", "--registry", default=None,
        help="Address of Registry contract, if not specified we read address from \"networks\"")


def add_p_metadata_file_opt(p):
    p.add_argument(
        "--metadata-file", default="service_metadata.json",
        help="Service metadata json file (default service_metadata.json)")


def add_p_organization_metadata_file_opt(p):
    p.add_argument(
        "--metadata-file", default="organization_metadata.json",
        help="Service metadata json file (default service_metadata.json)")


def add_p_org_id_service_id(p):
    add_p_org_id(p)
    p.add_argument("service_id", help="Id of service", metavar="SERVICE_ID")


def add_p_service_in_registry(p):
    add_p_org_id_service_id(p)
    add_p_registry_address_opt(p)


def add_mpe_account_options(parser):
    parser.set_defaults(cmd=MPEAccountCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True

    def add_p_snt_address_opt(p):
        p.add_argument(
            "--singularitynettoken-at", "--snt", default=None,
            help="Address of SingularityNetToken contract, if not specified we read address from \"networks\"")

    p = subparsers.add_parser("print", help="Print the current ETH account")
    p.set_defaults(fn="print_account")
    add_eth_call_arguments(p)

    p = subparsers.add_parser("balance", help="Print balance of ASI(FET) tokens and balance of MPE wallet")
    p.set_defaults(fn="print_token_and_mpe_balances")
    p.add_argument("--account", default=None, help="Account to print balance for (default is the current identity)")
    add_p_snt_address_opt(p)
    add_p_mpe_address_opt(p)
    add_eth_call_arguments(p)

    p = subparsers.add_parser("deposit", help="Deposit ASI(FET) tokens to MPE wallet")
    p.set_defaults(fn="deposit_to_mpe")
    p.add_argument("amount", type=strtoken2cogs, help="Amount of ASI(FET) tokens to deposit in MPE wallet", metavar="AMOUNT")
    add_p_snt_address_opt(p)
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("withdraw", help="Withdraw ASI(FET) tokens from MPE wallet")
    p.set_defaults(fn="withdraw_from_mpe")
    p.add_argument("amount", type=strtoken2cogs, help="Amount of ASI(FET) tokens to withdraw from MPE wallet", metavar="AMOUNT")
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("transfer", help="Transfer ASI(FET) tokens inside MPE wallet")
    p.set_defaults(fn="transfer_in_mpe")
    p.add_argument("receiver", help="Address of the receiver", metavar="RECEIVER")
    p.add_argument("amount",
                   type=strtoken2cogs,
                   help="Amount of ASI(FET) tokens to be transferred to another account inside MPE wallet",
                   metavar="AMOUNT")
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)


def add_p_channel_id(p):
    # int is ok here because in python3 int is unlimited
    p.add_argument("channel_id",
                   type=int,
                   help="The Channel Id",
                   metavar="CHANNEL_ID")


def add_p_channel_id_opt(p):
    p.add_argument("--channel-id",
                   type=int,
                   help="The Channel Id (only in case of multiply initialized channels for the same payment group)")


def add_p_endpoint(p):
    p.add_argument("endpoint",
                   help="Service endpoint",
                   metavar="ENDPOINT")


def add_group_name(p):
    p.add_argument("group_name",
                   default=None,
                   help="Name of the payment group. Parameter should be specified only for services with several payment groups")


def add_p_group_name(p):
    p.add_argument("--group-name",
                   default=None,
                   help="Name of the payment group. Parameter should be specified only for services with several payment groups")


def add_p_expiration(p, is_optional):
    h = "expiration time in blocks (<int>), or in blocks related to the current_block (+<int>blocks), or in days related to the current_block and assuming 15 sec/block (+<int>days)"
    if is_optional:
        p.add_argument("--expiration", help=h)
    else:
        p.add_argument("expiration",
                       help=h,
                       metavar="EXPIRATION")
    p.add_argument("--force",
                   action="store_true",
                   help="Skip check for very high (>6 month) expiration time")


def add_p_open_channel_basic(p):
    add_group_name(p)

    p.add_argument("amount",
                   type=strtoken2cogs,
                   help="Amount of ASI(FET) tokens to put in the new channel",
                   metavar="AMOUNT")
    # p.add_argument("group_name",
    #                default=None,
    #                help="Name of the payment group. Parameter should be specified only for services with several payment groups")

    add_p_expiration(p, is_optional=False)
    p.add_argument("--signer",
                   default=None,
                   help="Signer for the channel (by default is equal to the sender)")

    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)
    p.add_argument("--open-new-anyway",
                   action="store_true",
                   help="Skip check that channel already exists and open new channel anyway")


def add_mpe_channel_options(parser):
    parser.set_defaults(cmd=MPEChannelCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True

    p = subparsers.add_parser("open",
                              help="Open channel using organization metadata from Registry")
    p.set_defaults(fn="open_channel_from_registry")

    add_p_org_id(p)
    add_p_registry_address_opt(p)
    add_p_open_channel_basic(p)

    p = subparsers.add_parser("open-from-metadata",
                              help="Open channel using existing organization metadata")
    p.set_defaults(fn="open_channel_from_metadata")
    add_p_org_id(p)
    add_p_registry_address_opt(p)
    add_p_open_channel_basic(p)
    add_p_organization_metadata_file_opt(p)

    def add_p_set_for_extend_add(_p):
        expiration_amount_g = _p.add_argument_group(
            title="Expiration and amount")
        add_p_expiration(expiration_amount_g, is_optional=True)
        expiration_amount_g.add_argument("--amount",
                                         type=strtoken2cogs,
                                         help="Amount of ASI(FET) tokens to add to the channel")
        add_p_mpe_address_opt(p)
        add_transaction_arguments(p)

    p = subparsers.add_parser("extend-add", help="Set new expiration for the channel and add funds")
    p.set_defaults(fn="channel_extend_and_add_funds")
    add_p_channel_id(p)
    add_p_set_for_extend_add(p)

    p = subparsers.add_parser("extend-add-for-org",
                              help="Set new expiration and add funds for the channel for the given service (organization and group name)")
    p.set_defaults(fn="channel_extend_and_add_funds_for_org")
    add_p_org_id(p)
    add_group_name(p)
    add_p_registry_address_opt(p)
    add_p_set_for_extend_add(p)
    add_p_group_name(p)
    add_p_channel_id_opt(p)

    p = subparsers.add_parser("block-number",
                              help="Print the last ethereum block number")
    p.set_defaults(fn="print_block_number")

    def add_p_only_id(_p):
        _p.add_argument("--only-id",
                        action='store_true',
                        help="Print only id of channels",
                        default=False)

    def add_p_sender(_p):
        _p.add_argument("--sender",
                        default=None,
                        help="Account to set as sender (by default we use the current identity)")

    def add_p_dont_sync_channels(_p):
        _p.add_argument("--do-not-sync", "-ds",
                        action='store_true',
                        help="Print channels without synchronizing their state",
                        default=False)

    p = subparsers.add_parser("print-filter-sender",
                              help="Print all channels for the given sender.")
    p.set_defaults(fn="print_channels_filter_sender")
    add_p_only_id(p)
    add_p_mpe_address_opt(p)
    add_eth_call_arguments(p)
    add_p_sender(p)
    add_p_dont_sync_channels(p)

    p = subparsers.add_parser("print-filter-recipient",
                              help="Print all channels for the given recipient.")
    p.set_defaults(fn="print_channels_filter_recipient")
    add_p_only_id(p)
    add_p_mpe_address_opt(p)
    add_eth_call_arguments(p)
    p.add_argument("--recipient",
                   default=None,
                   help="Account to set as recipient (by default we use the current identity)")
    add_p_dont_sync_channels(p)

    p = subparsers.add_parser("print-filter-group",
                              help="Print all channels for the given service.")
    p.set_defaults(fn="print_channels_filter_group")
    add_p_org_id(p)
    add_group_name(p)
    add_p_registry_address_opt(p)
    add_p_only_id(p)
    add_p_mpe_address_opt(p)
    add_eth_call_arguments(p)
    add_p_dont_sync_channels(p)

    p = subparsers.add_parser("print-filter-group-sender",
                              help="Print all channels for the given group and sender.")
    p.set_defaults(fn="print_channels_filter_group_sender")
    add_p_org_id(p)
    add_group_name(p)
    add_p_registry_address_opt(p)
    add_p_only_id(p)
    add_p_mpe_address_opt(p)
    add_eth_call_arguments(p)
    add_p_sender(p)
    add_p_dont_sync_channels(p)

    p = subparsers.add_parser("print-all",
                              help="Print all channels.")
    p.set_defaults(fn="print_all_channels")
    add_p_registry_address_opt(p)
    add_p_only_id(p)
    add_p_mpe_address_opt(p)
    add_eth_call_arguments(p)
    add_p_dont_sync_channels(p)

    p = subparsers.add_parser("claim-timeout",
                              help="Claim timeout of the channel")
    p.set_defaults(fn="channel_claim_timeout")
    add_p_channel_id(p)
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("claim-timeout-all",
                              help="Claim timeout for all channels which have current identity as a sender.")
    p.set_defaults(fn="channel_claim_timeout_all")
    add_p_mpe_address_opt(p)
    add_transaction_arguments(p)


def add_mpe_client_options(parser):
    parser.set_defaults(cmd=MPEClientCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True

    def add_p_set1_for_call(_p):
        _p.add_argument("--service",
                        default=None,
                        help="Name of protobuf service to call. It should be specified in case of method name conflict.")
        _p.add_argument("method",
                        help="Target service's method name to call",
                        metavar="METHOD")
        _p.add_argument("params",
                        nargs='?',
                        help="JSON-serialized parameters object or path containing "
                             "JSON-serialized parameters object (leave emtpy to read from stdin)",
                        metavar="PARAMS")
        add_eth_call_arguments(_p)

        add_p_mpe_address_opt(_p)
        _p.add_argument("--save-response",
                        default=None,
                        help="Save response in the file",
                        metavar="FILENAME")
        _p.add_argument("--save-field",
                        default=None,
                        nargs=2,
                        help="Save specific field in the file (two arguments 'field' and 'file_name' should be specified)")
        _p.add_argument("--endpoint",
                        help="Service endpoint (by default we read it from metadata)")
        # p.add_argument("group-name",
        #                default=None,
        #                help="Name of the payment group. Parameter should be specified only for services with several payment groups")

    # call: testo tests method params --endpoint --group-name
    p = subparsers.add_parser("call",
                              help="Call server. We ask state of the channel from the server if needed. Channel should be already initialized.")
    p.set_defaults(fn="call_server_statelessly")
    add_p_org_id_service_id(p)
    add_group_name(p)
    add_p_set1_for_call(p)
    add_p_channel_id_opt(p)
    p.add_argument("--yes", "-y",
                   action="store_true",
                   help="Skip interactive confirmation of call price",
                   default=False)
    p.add_argument("--skip-update-check",
                   action="store_true",
                   help="Skip check for service update",
                   default=False)

    p = subparsers.add_parser("call-lowlevel",
                              help="Low level function for calling the server. Service should be already initialized.")
    p.set_defaults(fn="call_server_lowlevel")
    add_p_org_id_service_id(p)
    add_group_name(p)
    add_p_channel_id(p)
    p.add_argument("nonce",
                   type=int,
                   help="Nonce of the channel",
                   metavar="NONCE")
    p.add_argument("amount_in_cogs",
                   type=int,
                   help="Amount in cogs",
                   metavar="AMOUNT_IN_COGS")
    add_p_set1_for_call(p)

    p = subparsers.add_parser("get-channel-state",
                              help="Get channel state in stateless manner")
    p.set_defaults(fn="print_channel_state_statelessly")
    add_p_mpe_address_opt(p)
    add_p_channel_id(p)
    add_p_endpoint(p)
    add_eth_call_arguments(p)


def add_mpe_service_options(parser):
    parser.set_defaults(cmd=MPEServiceCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True

    p = subparsers.add_parser("metadata-init-utility",
                              help="Utility to create service metadata file")
    p.set_defaults(fn="service_metadata_init")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-init",
                              help="Init metadata file with providing protobuf directory (which we publish in IPFS or FileCoin) and display_name (optionally encoding, service_type and payment_expiration_threshold)")
    p.set_defaults(fn="publish_proto_metadata_init")
    p.add_argument("protodir",
                   help="Directory which contains protobuf files",
                   metavar="PROTO_DIR")
    add_p_metadata_file_opt(p)
    add_p_mpe_address_opt(p)
    p.add_argument("display_name",
                   help="Service display name",
                   metavar="DISPLAY_NAME")
    p.add_argument("--group-name",
                   help="Name of the first payment group")
    p.add_argument("--endpoints",
                   default=[],
                   nargs='*',
                   help="Endpoints for the first group")
    p.add_argument("--fixed-price",
                   type=strtoken2cogs,
                   help="Set fixed price in ASI(FET) token for all methods")

    p.add_argument("--encoding",
                   default="proto",
                   choices=['proto', 'json'],
                   help="Service encoding")

    p.add_argument("--service-type",
                   default="grpc",
                   choices=['grpc', 'http', 'jsonrpc', 'process'],
                   help="Service type")
    add_p_storage_param(p)

    p = subparsers.add_parser("metadata-set-api",
                              help="Publish protobuf model in ipfs or filecoin and update existed metadata file")
    p.set_defaults(fn="publish_proto_metadata_update")
    p.add_argument("protodir",
                   help="Directory which contains protobuf files",
                   metavar="PROTO_DIR")
    add_p_metadata_file_opt(p)
    add_p_storage_param(p)

    p = subparsers.add_parser("metadata-set-fixed-price",
                              help="Set pricing model as fixed price for all methods")
    p.set_defaults(fn="metadata_set_fixed_price")

    p.add_argument("group_name",
                   help="group name for fixed price method")
    p.add_argument("price",
                   type=strtoken2cogs,
                   help="Set fixed price in ASI(FET) token for all methods",
                   metavar="PRICE")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-set-method-price",
                              help="Set pricing model as method price for all methods")
    p.set_defaults(fn="metadata_set_method_price")

    p.add_argument("group_name",
                   help="group name")
    p.add_argument("package_name",
                   help="package name ")
    p.add_argument("service_name",
                   help="service name")
    p.add_argument("method",
                   help="method for which price need to be set",
                   )

    p.add_argument("price",
                   type=strtoken2cogs,
                   help="Set fixed price in ASI(FET) token for all methods",
                   metavar="PRICE")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-add-group",
                              help="Add new group of replicas")
    p.set_defaults(fn="metadata_add_group")
    add_p_metadata_file_opt(p)
    p.add_argument("group_name",
                   help="Name of the  payment group",
                   metavar="GROUP_NAME")

    p = subparsers.add_parser("metadata-remove-group",
                              help="remove group from service")
    p.set_defaults(fn="metadata_remove_group")
    add_p_metadata_file_opt(p)
    p.add_argument("group_name",
                   help="Name of the  payment group",
                   metavar="GROUP_NAME")

    p = subparsers.add_parser("metadata-add-daemon-addresses", help="add Ethereum public addresses of daemon in given payment group of service")
    p.set_defaults(fn="metadata_add_daemon_addresses")
    p.add_argument("group_name", default=None,
                   help="Name of the payment group to which we want to add daemon addresses")
    p.add_argument("daemon_addresses", nargs="+", help="Ethereum public addresses of daemon",
                   metavar="DAEMON ADDRESSES")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-all-daemon-addresses",
                              help="Remove all daemon addresses from metadata")
    p.set_defaults(fn="metadata_remove_all_daemon_addresses")
    p.add_argument("group_name", default=None,
                   help="Name of the payment group to which we want to remove endpoints")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-update-daemon-addresses", help="Update daemon addresses to the groups")
    p.set_defaults(fn="metadata_update_daemon_addresses")
    p.add_argument("group_name", default=None,
                   help="Name of the payment group to which we want to update daemon addresses")
    p.add_argument("daemon_addresses", nargs="+", help="Daemon addresses",
                   metavar="DAEMON ADDRESSES")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-add-endpoints",
                              help="Add daemon endpoints to the groups")
    p.set_defaults(fn="metadata_add_endpoints")
    p.add_argument("group_name",
                   default=None,
                   help="Name of the payment group to which we want to add endpoints")

    p.add_argument("endpoints",
                   nargs="+",
                   help="Endpoints",
                   metavar="ENDPOINTS")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-all-endpoints",
                              help="Remove all endpoints from metadata")
    p.add_argument("group_name",
                   default=None,
                   help="Name of the payment group to which we want to remove endpoints")

    p.set_defaults(fn="metadata_remove_all_endpoints")

    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-set-free-calls", help="Set free calls for group for service")
    p.set_defaults(fn="metadata_set_free_calls")
    add_p_metadata_file_opt(p)
    p.add_argument("group_name", help="Name of the payment group to which we want to set freecalls",
                   metavar="GROUP_NAME")
    p.add_argument("free_calls", default=0, type=int, help="Number of free calls")

    p = subparsers.add_parser("metadata-set-freecall-signer-address", help="Set free calls for group for service")
    p.set_defaults(fn="metadata_set_freecall_signer_address")
    add_p_metadata_file_opt(p)
    p.add_argument("group_name", help="Name of the payment group to which we want to set freecalls",
                   metavar="GROUP_NAME")
    p.add_argument(
        "signer_address",
        help="This is used to define the public key address used for validating signatures "
             "requested specially for free call. To be obtained as part of curation process")

    p = subparsers.add_parser("metadata-add-assets",
                              help="Add assets to metadata, valid asset types are [hero_image,images]")
    p.set_defaults(fn="metadata_add_asset_to_ipfs")
    p.add_argument("asset_file_path",
                   help="Asset file path")
    p.add_argument("asset_type",
                   help="Type of the asset")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-assets",
                              help="Remove asset of a given type valid asset types are [hero_image,images]")
    p.set_defaults(fn="metadata_remove_assets_of_a_given_type")
    p.add_argument("asset_type",
                   help="Type of the asset to be removed , valid asset types are [hero_image,images]")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-all-assets",
                              help="Remove all assets from metadata")
    p.set_defaults(fn="metadata_remove_all_assets")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-add-media",
                              help="Add media to metadata")
    p.set_defaults(fn="metadata_add_media")
    p.add_argument("media_url",
                   metavar='MEDIA_URL',
                   help="Media url endpoint")
    p.add_argument('--hero_image',
                   help='Indicate whether hero-image (default False)',
                   action='store_true')
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-media",
                              help="Remove media of asset type")
    p.set_defaults(fn="metadata_remove_media")
    p.add_argument("order",
                   metavar="ORDER",
                   help="Delete by order of media",
                   type=int)
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-remove-all-media",
                              help="Remove all existing media")
    p.set_defaults(fn="metadata_remove_all_media")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-swap-media-order",
                              help="Swap media order")
    p.set_defaults(fn="metadata_swap_media_order")
    p.add_argument("move_from",
                   metavar="FROM",
                   help="Order number to swap from",
                   type=int)
    p.add_argument("move_to",
                   metavar="TO",
                   help="Order number to swap to",
                   type=int)
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-change-media-order",
                              help="Reassign all individual media order")
    p.set_defaults(fn="metadata_change_media_order")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-update-endpoints",
                              help="Remove all endpoints from the group and add new ones")
    p.set_defaults(fn="metadata_update_endpoints")
    p.add_argument("group_name",
                   default=None,
                   help="Name of the payment group to which we want to update endpoints")
    p.add_argument("endpoints",
                   nargs="+",
                   help="Endpoints")

    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-add-description",
                              help="Add service description")
    p.set_defaults(fn="metadata_add_description")
    p.add_argument("--json",
                   default=None,
                   help="Service description in json")
    p.add_argument("--url",
                   default=None,
                   help="URL to provide more details of the service")
    p.add_argument("--description",
                   default=None,
                   help="Some description of what the service does", metavar="DESCRIPTION")
    p.add_argument("--short-description",
                   default=None,
                   help="Some short description for overview")
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("metadata-add-contributor", help="Add contributor")
    p.set_defaults(fn="metadata_add_contributor")
    add_p_metadata_file_opt(p)
    p.add_argument("name", help="Name of the contributor")
    p.add_argument("email_id", help="Email of the contributor")

    p = subparsers.add_parser("metadata-remove-contributor", help="Add contributor")
    p.set_defaults(fn="metadata_remove_contributor")
    add_p_metadata_file_opt(p)
    p.add_argument("email_id", help="Email of the contributor")

    p = subparsers.add_parser("validate-metadata",
                              help="Validates if created metadata is consistent")
    p.set_defaults(fn="metadata_validate")
    add_p_metadata_file_opt(p)

    def add_p_publish_params(_p):
        add_p_metadata_file_opt(_p)
        _p.add_argument("--update-mpe-address",
                        action='store_true',
                        help="Update mpe_address in metadata before publishing them")
        add_p_mpe_address_opt(_p)

    p = subparsers.add_parser("publish",
                              help="Publish service with given metadata")
    p.set_defaults(fn="publish_service_with_metadata")
    add_p_publish_params(p)
    add_p_service_in_registry(p)
    add_transaction_arguments(p)
    add_p_storage_param(p)

    p = subparsers.add_parser("publish-in-ipfs",
                              help="Publish metadata only in IPFS, without publishing in Registry")
    p.set_defaults(fn="publish_metadata_in_ipfs")
    add_p_publish_params(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("publish-in-filecoin",
                              help="Publish metadata only in FileCoin, without publishing in Registry")
    p.set_defaults(fn="publish_metadata_in_filecoin")
    add_p_publish_params(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("update-metadata",
                              help="Publish metadata in IPFS or FileCoin and update existed service")
    p.set_defaults(fn="publish_metadata_in_storage_and_update_registration")
    add_p_publish_params(p)
    add_p_service_in_registry(p)
    add_transaction_arguments(p)
    add_p_storage_param(p)

    p = subparsers.add_parser("update-add-tags",
                              help="Add tags to existed service registration")
    p.set_defaults(fn="update_registration_add_tags")
    add_p_service_in_registry(p)
    p.add_argument("tags",
                   nargs="+",
                   default=[],
                   help="Tags which will be add",
                   metavar="TAGS")
    add_transaction_arguments(p)

    p = subparsers.add_parser("update-remove-tags",
                              help="Remove tags from existed service registration")
    p.set_defaults(fn="update_registration_remove_tags")
    add_p_service_in_registry(p)
    p.add_argument("tags",
                   nargs="+",
                   default=[],
                   help="Tags which will be removed",
                   metavar="TAGS")
    add_transaction_arguments(p)


    p = subparsers.add_parser("print-metadata",
                              help="Print service metadata from registry")
    p.set_defaults(fn="print_service_metadata_from_registry")
    add_p_service_in_registry(p)

    p = subparsers.add_parser("metadata-add-tags",
                              help="Add new tags to service")
    p.set_defaults(fn="metadata_add_tags")
    add_p_metadata_file_opt(p)
    p.add_argument("tags",
                   nargs="+",
                   default=[],
                   help="Tags to add",
                   metavar="TAGS")

    p = subparsers.add_parser("metadata-remove-tags",
                              help="Remove tags from service")
    p.set_defaults(fn="metadata_remove_tags")
    add_p_metadata_file_opt(p)
    p.add_argument("tags",
                   nargs="+",
                   default=[],
                   help="Tags to removed",
                   metavar="TAGS")

    p = subparsers.add_parser("print-service-status",
                              help="Print service status")
    p.set_defaults(fn="print_service_status")
    add_p_service_in_registry(p)
    add_p_group_name(p)

    p = subparsers.add_parser("print-tags",
                              help="Print tags for given service from registry")
    p.set_defaults(fn="print_service_tags_from_registry")
    add_p_service_in_registry(p)

    def add_p_protodir_to_extract(_p):
        _p.add_argument("protodir",
                        help="Directory to which extract api (model)",
                        metavar="PROTO_DIR")

    p = subparsers.add_parser("get-api-metadata",
                              help="Extract service api (model) to the given protodir. Get existed metadata")
    p.set_defaults(fn="extract_service_api_from_metadata")
    add_p_protodir_to_extract(p)
    add_p_metadata_file_opt(p)

    p = subparsers.add_parser("get-api-registry",
                              help="Extract service api (model) to the given protodir. Get metadata from registry")
    p.set_defaults(fn="extract_service_api_from_registry")
    add_p_service_in_registry(p)
    add_p_protodir_to_extract(p)

    p = subparsers.add_parser("delete",
                              help="Delete service registration from registry")
    p.set_defaults(fn="delete_service_registration")
    add_p_service_in_registry(p)
    add_transaction_arguments(p)

def add_mpe_treasurer_options(parser):
    parser.set_defaults(cmd=MPETreasurerCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True

    def add_p_daemon_endpoint(_p):
        _p.add_argument("--endpoint",
                        required=True,
                        help="Daemon endpoint")

    p = subparsers.add_parser("print-unclaimed",
                              help="Print unclaimed payments")
    p.set_defaults(fn="print_unclaimed")
    add_p_daemon_endpoint(p)
    add_eth_call_arguments(p)

    p = subparsers.add_parser("claim",
                              help="Claim given channels. We also claim all pending 'payments in progress' in case we 'lost' some payments.")
    p.set_defaults(fn="claim_channels")
    p.add_argument("channels",
                   type=int,
                   nargs="+",
                   help="Channels to claim",
                   metavar="CHANNELS")
    add_p_daemon_endpoint(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("claim-all",
                              help="Claim all channels. We also claim all pending 'payments in progress' in case we 'lost' some payments.")
    p.set_defaults(fn="claim_all_channels")
    add_p_daemon_endpoint(p)
    add_transaction_arguments(p)

    p = subparsers.add_parser("claim-expired",
                              help="Claim all channels which are close to expiration date. We also claim all pending 'payments in progress' in case we 'lost' some payments.")
    p.set_defaults(fn="claim_almost_expired_channels")
    p.add_argument("--expiration-threshold",
                   type=int,
                   default=34560,
                   help="Service expiration threshold in blocks (default is 34560 ~ 6 days with 15s/block)")
    add_p_daemon_endpoint(p)
    add_transaction_arguments(p)


def add_sdk_options(parser):
    parser.set_defaults(cmd=SDKCommand)
    subparsers = parser.add_subparsers(title="Commands", metavar="COMMAND")
    subparsers.required = True

    p = subparsers.add_parser("generate-client-library",
                              help="Generate compiled client libraries to call services using Python")
    p.set_defaults(fn="generate_client_library")
    add_p_service_in_registry(p)
    p.add_argument("protodir",
                   nargs="?",
                   default="client_libraries",
                   help="Directory where to output the generated client libraries",
                   metavar="PROTO_DIR")
    add_eth_call_arguments(p)
