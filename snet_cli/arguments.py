import argparse
import os
import re
import sys
from pathlib import Path

from snet_cli.commands import IdentityCommand, SessionCommand, NetworkCommand, ContractCommand, AgentFactoryCommand, \
    AgentCommand, ServiceCommand, ClientCommand, OrganizationCommand
from snet_cli.identity import get_identity_types
from snet_cli.session import get_session_keys
from snet_cli.utils import type_converter, get_contract_def


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
    add_root_options(parser, config)

    return parser


def add_root_options(parser, config):
    subparsers = parser.add_subparsers(title="snet commands", metavar="COMMAND")
    subparsers.required = True

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

    agent_p = subparsers.add_parser("agent", help="Interact with the SingularityNET Agent contract")
    add_agent_options(agent_p)

    agent_factory_p = subparsers.add_parser("agent-factory",
                                            help="Interact with the SingularityNET AgentFactory contract")
    add_agent_factory_options(agent_factory_p)

    client_p = subparsers.add_parser("client", help="Interact with SingularityNET services")
    add_client_options(client_p)

    contract_p = subparsers.add_parser("contract", help="Interact with contracts at a low level")
    add_contract_options(contract_p)

    service_p = subparsers.add_parser("service", help="Create, publish, register, and update SingularityNET services")
    add_service_options(service_p, config)

    organization_p = subparsers.add_parser("organization", help="Interact with SingularityNET Organizations")
    add_organization_options(organization_p, config)


def add_identity_options(parser, config):
    parser.set_defaults(cmd=IdentityCommand)
    parser.set_defaults(fn="list")
    subparsers = parser.add_subparsers(title="actions", metavar="ACTION")

    identity_names = list(
        map(lambda x: x[len("identity."):], filter(lambda x: x.startswith("identity."), config.sections())))

    create_p = subparsers.add_parser("create", help="Create a new identity")
    create_p.set_defaults(fn="create")
    create_p.add_argument("identity_name", help="name of identity to create", metavar="IDENTITY_NAME")
    create_p.add_argument("identity_type", choices=get_identity_types(),
                          help="type of identity to create from {}".format(get_identity_types()),
                          metavar="IDENTITY_TYPE")
    create_p.add_argument("--mnemonic", help="bip39 mnemonic for 'mnemonic' identity_type")
    create_p.add_argument("--private-key", help="hex-encoded private key for 'key' identity_type")
    create_p.add_argument("--eth-rpc-endpoint", help="ethereum json-rpc endpoint for 'rpc' identity_type")

    delete_p = subparsers.add_parser("delete", help="Delete an identity")
    delete_p.set_defaults(fn="delete")
    delete_p.add_argument("identity_name", choices=identity_names,
                          help="name of identity to delete from {}".format(identity_names), metavar="IDENTITY_NAME")

    for identity_name in identity_names:
        p = subparsers.add_parser(identity_name, help="Switch to {} identity".format(identity_name))
        p.set_defaults(identity_name=identity_name)
        p.set_defaults(fn="set")


def add_network_options(parser, config):
    parser.set_defaults(cmd=NetworkCommand)
    parser.set_defaults(fn="list")
    subparsers = parser.add_subparsers(title="networks", metavar="NETWORK")

    network_names = list(
        map(lambda x: x[len("network."):], filter(lambda x: x.startswith("network."), config.sections())))

    for network_name in network_names:
        p = subparsers.add_parser(network_name, help="Switch to {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        p.set_defaults(fn="set")

    p = subparsers.add_parser("eth-rpc-endpoint", help="Switch to an endpoint-determined network")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.set_defaults(fn="set")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')", metavar="ETH_RPC_ENDPOINT")


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
    parser.add_argument("key", choices=get_session_keys(),
                        help="session key to unset from {}".format(get_session_keys()), metavar="KEY")


def add_agent_options(parser):
    parser.set_defaults(cmd=AgentCommand)

    add_contract_identity_arguments(parser, [("", "agent_at")])

    subparsers = parser.add_subparsers(title="agent commands", metavar="COMMAND")
    subparsers.required = True

    create_jobs_p = subparsers.add_parser("create-jobs", help="Create jobs")
    create_jobs_p.set_defaults(fn="create_jobs")
    create_jobs_p.add_argument("--number", "-n", type=int, default=1, help="number of jobs to create (defaults to 1)")
    create_jobs_p.add_argument("--max-price", type=int, default=0,
                               help="skip interactive confirmation of job price if below max price (defaults to 0)")
    create_jobs_p.add_argument("--funded", action="store_true", help="fund created jobs", default=False)
    create_jobs_p.add_argument("--signed", action="store_true", help="generate job signatures for created jobs",
                               default=False)
    add_transaction_arguments(create_jobs_p)


def add_agent_factory_options(parser):
    parser.set_defaults(cmd=AgentFactoryCommand)

    add_contract_identity_arguments(parser, [("", "agent_factory_at")])

    subparsers = parser.add_subparsers(title="agent-factory commands", metavar="COMMAND")
    subparsers.required = True

    create_agent_p = subparsers.add_parser("create-agent", help="Create an agent")
    create_agent_p.set_defaults(fn="create_agent")
    create_agent_p.add_argument("contract_named_input_price", type=type_converter("uint256"), metavar="PRICE",
                  help="initial price for interacting with the service")
    create_agent_p.add_argument("contract_named_input_endpoint", type=type_converter("string"), metavar="ENDPOINT",
                  help="initial endpoint to call the service's API")
    create_agent_p.add_argument("contract_named_input_metadataURI", type=type_converter("string"), metavar="METADATA_URI",
                                 nargs="?", default="", help="uri where service metadata is stored")
    add_transaction_arguments(create_agent_p)


def add_client_options(parser):
    parser.set_defaults(cmd=ClientCommand)

    subparsers = parser.add_subparsers(title="client commands", metavar="COMMAND")
    subparsers.required = True

    call_p = subparsers.add_parser("call", help="Call a service")
    call_p.set_defaults(fn="call")
    call_p.add_argument("method", help="target service's method name to call", metavar="METHOD")
    call_p.add_argument("params", nargs='?', help="json-serialized parameters object or path containing "
                                                  "json-serialized parameters object (leave emtpy to read from stdin)",
                        metavar="PARAMS")
    call_p.add_argument("--max-price", type=int, default=0,
                        help="skip interactive confirmation of job price if below max price (defaults to 0)")
    add_contract_identity_arguments(call_p, [("agent", "agent_at"), ("job", "job_at")])
    add_transaction_arguments(call_p)

    get_spec_p = subparsers.add_parser("get-spec", help="Get a service's spec file")
    get_spec_p.set_defaults(fn="get_spec")
    get_spec_p.add_argument("dest_dir", help="destination directory for service's spec files", metavar="DEST_DIR")
    add_contract_identity_arguments(get_spec_p, [("agent", "agent_at")])


def add_contract_options(parser):
    parser.set_defaults(cmd=ContractCommand)

    subparsers = parser.add_subparsers(title="contracts", metavar="CONTRACT")
    subparsers.required = True

    for path in Path(__file__).absolute().parent.joinpath("resources", "contracts", "abi").glob("*json"):
        contract_name = re.search(r"([^.]*)\.json", os.path.basename(path)).group(1)
        contract_p = subparsers.add_parser(contract_name, help="{} contract".format(contract_name))
        add_contract_function_options(contract_p, contract_name)


def _add_service_publish_arguments(parser):
    parser.add_argument("--no-register", action="store_true", help="does not register the published service")
    parser.add_argument("--config", help="specify a custom service.json file path")
    add_transaction_arguments(parser)
    add_contract_identity_arguments(parser, [("registry", "registry_at"), ("agent-factory", "agent_factory_at")])


def _add_service_update_arguments(parser):
    parser.set_defaults(fn="update")
    parser.add_argument("--new-price", help="new price to call the service", type=type_converter("uint256"))
    parser.add_argument("--new-endpoint", help="new endpoint to call the service's API")
    parser.add_argument("--new-tags", nargs="+", type=type_converter("bytes32"),
                        metavar=("TAGS", "TAG1, TAG2,"), help="new list of tags you want associated with the service registration")
    parser.add_argument("--new-description", help="new description for the service")
    parser.add_argument("--config", help="specify a custom service.json file path")
    add_transaction_arguments(parser)
    add_contract_identity_arguments(parser, [("registry", "registry_at")])


def _add_organization_arguments(parser):
    add_transaction_arguments(parser)
    add_contract_identity_arguments(parser, [("registry", "registry_at")])


def add_service_options(parser, config):
    parser.set_defaults(cmd=ServiceCommand)

    subparsers = parser.add_subparsers(title="service commands", metavar="COMMAND")
    subparsers.required = True

    init_p = subparsers.add_parser("init", help="Initialize a service package on the filesystem")
    init_p.set_defaults(fn="init")
    init_p.add_argument("--name", help='name of the service to be stored in the registry (default: <current working directory>)')
    init_p.add_argument("--spec", help='local filesystem path to the service spec directory (default: "service_spec/")')
    init_p.add_argument("--organization", help='the organization to which you want to register the service (default: "")')
    init_p.add_argument("--path", help='the path under which you want to register the service in the organization (default: "")')
    init_p.add_argument("--price", help='initial price for interacting with the service (default: 0)', type=int)
    init_p.add_argument("--endpoint", help="initial endpoint to call the service's API (default: \"\")")
    init_p.add_argument("--tags", nargs="+", metavar=("TAGS", "TAG1, TAG2,"), help="tags to describe the service (default: [])")
    init_p.add_argument("--description",
                        help='human-readable description of the service (default: "")')
    init_p.add_argument("-y", action="store_true", help="accept defaults for any argument that is not provided")

    network_names = list(
        map(lambda x: x[len("network."):], filter(lambda x: x.startswith("network."), config.sections())))

    publish_p = subparsers.add_parser("publish", help="Publish a service to the network", default_choice="default")
    publish_p.set_defaults(fn="publish")
    networks_publish_subparsers = publish_p.add_subparsers(title="networks", metavar="[NETWORK]")

    for network_name in network_names:
        p = networks_publish_subparsers.add_parser(network_name, help="Publish a service to {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_service_publish_arguments(p)

    p = networks_publish_subparsers.add_parser("eth-rpc-endpoint", help="Publish a service using the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')", metavar="ETH_RPC_ENDPOINT")
    _add_service_publish_arguments(p)

    p = networks_publish_subparsers.add_parser("default")
    _add_service_publish_arguments(p)

    update_p = subparsers.add_parser("update", help="Update a service on the network", default_choice="default")
    update_p.set_defaults(fn="update")
    networks_update_subparsers = update_p.add_subparsers(title="networks", metavar="[NETWORK]")

    for network_name in network_names:
        p = networks_update_subparsers.add_parser(network_name, help="Update a service on {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_service_update_arguments(p)

    p = networks_update_subparsers.add_parser("eth-rpc-endpoint", help="Update a service using the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')", metavar="ETH_RPC_ENDPOINT")
    _add_service_update_arguments(p)

    p = networks_update_subparsers.add_parser("default")
    _add_service_update_arguments(p)


def add_organization_options(parser, config):
    parser.set_defaults(cmd=OrganizationCommand)

    subparsers = parser.add_subparsers(title="organization commands", metavar="COMMAND")
    subparsers.required = True

    network_names = list(
        map(lambda x: x[len("network."):], filter(lambda x: x.startswith("network."), config.sections())))

    org_list_p = subparsers.add_parser("list", help="List Organizations", default_choice="default")
    org_list_p.set_defaults(fn="list")
    networks_organization_subparsers = org_list_p.add_subparsers(title="networks", metavar="[NETWORK]")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name,
                                                        help="List Organizations from {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint",
                                                    help="List Organizations at the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')",
                   metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)

    org_info_p = subparsers.add_parser("info", help="Organization's Informations", default_choice="default")
    org_info_p.set_defaults(fn="info")
    networks_organization_subparsers = org_info_p.add_subparsers(title="networks", metavar="[NETWORK]")
    org_info_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name,
                                                        help="Organization's Informations from {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint",
                                                    help="Organization's Informations at the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')",
                   metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)

    org_create_p = subparsers.add_parser("create", help="Create an Organization", default_choice="default")
    org_create_p.set_defaults(fn="create")
    networks_organization_subparsers = org_create_p.add_subparsers(title="networks", metavar="[NETWORK]")
    org_create_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_create_p.add_argument("members", help="List of members to be added to the organization",
                              metavar="ORG_MEMBERS[]")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name, help="Create an Organization on {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint", help="Create an Organization using the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')", metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)

    org_delete_p = subparsers.add_parser("delete", help="Delete an Organization", default_choice="default")
    org_delete_p.set_defaults(fn="delete")
    networks_organization_subparsers = org_delete_p.add_subparsers(title="networks", metavar="[NETWORK]")
    org_delete_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name, help="Delete an Organization from {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint",
                                                    help="Delete an Organization at the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')",
                   metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)

    org_list_services_p = subparsers.add_parser("list-services", help="List Organization's services", default_choice="default")
    org_list_services_p.set_defaults(fn="list_services")
    networks_organization_subparsers = org_list_services_p.add_subparsers(title="networks", metavar="[NETWORK]")
    org_list_services_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name,help="List Organization's services from {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint",
                                                    help="List Organization's services at the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')",
                   metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)

    org_change_owner_p = subparsers.add_parser("change-owner", help="Change Organization's owner",
                                               default_choice="default")
    org_change_owner_p.set_defaults(fn="change_owner")
    networks_organization_subparsers = org_change_owner_p.add_subparsers(title="networks", metavar="[NETWORK]")
    org_change_owner_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_change_owner_p.add_argument("owner", help="Address of the new Organization's owner", metavar="OWNER_NAME")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name, help="List Organization's services from {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint",
                                                    help="Change Organization's owner at the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')",
                   metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)

    org_add_members_p = subparsers.add_parser("add-members", help="Add members to Organization",
                                              default_choice="default")
    org_add_members_p.set_defaults(fn="add_members")
    networks_organization_subparsers = org_add_members_p.add_subparsers(title="networks", metavar="[NETWORK]")
    org_add_members_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_add_members_p.add_argument("members", help="List of members to be added to the organization",
                                   metavar="ORG_MEMBERS[]")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name,
                                                        help="Add members to Organization on {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint",
                                                    help="Add members to Organization using the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')",
                   metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)

    org_rm_members_p = subparsers.add_parser("rem-members", help="Remove members from Organization",
                                             default_choice="default")
    org_rm_members_p.set_defaults(fn="rem_members")
    networks_organization_subparsers = org_rm_members_p.add_subparsers(title="networks", metavar="[NETWORK]")
    org_rm_members_p.add_argument("name", help="Name of the Organization", metavar="ORG_NAME")
    org_rm_members_p.add_argument("members", help="List of members to be removed from the organization",
                                  metavar="ORG_MEMBERS[]")

    for network_name in network_names:
        p = networks_organization_subparsers.add_parser(network_name,
                                                        help="Remove members from Organization on {} network".format(network_name))
        p.set_defaults(network_name=network_name)
        _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("eth-rpc-endpoint",
                                                    help="Remove members from Organization using the provided Ethereum-RPC endpoint")
    p.set_defaults(network_name="eth_rpc_endpoint")
    p.add_argument("eth_rpc_endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')",
                   metavar="ETH_RPC_ENDPOINT")
    _add_organization_arguments(p)

    p = networks_organization_subparsers.add_parser("default")
    _add_organization_arguments(p)


def add_contract_function_options(parser, contract_name):
    add_contract_identity_arguments(parser)

    contract_def = get_contract_def(contract_name)
    parser.set_defaults(contract_def=contract_def)

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


def add_transaction_arguments(parser):
    transaction_g = parser.add_argument_group(title="transaction arguments")
    transaction_g.add_argument("--gas-price", type=int,
                               help="ethereum gas price for transaction (defaults to session.default_gas_price)")
    transaction_g.add_argument("--eth-rpc-endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://'; "
                                                          "defaults to session.identity.eth_rpc_endpoint or "
                                                          "session.default_eth_rpc_endpoint)")
    transaction_g.add_argument("--wallet-index", type=int,
                               help="wallet index of account to use for signing (defaults to session.default_wallet"
                                    " index)")
    transaction_g.add_argument("--no-confirm", action="store_true",
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
