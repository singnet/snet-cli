import argparse
import json
import os
import re
import sys
from pathlib import Path

from snet_cli.commands import IdentityCommand, SessionCommand, NetworkCommand, ContractCommand, \
    AgentFactoryCommand, RegistryCommand, AgentCommand, ClientCommand
from snet_cli.identity import get_identity_types
from snet_cli.session import get_session_keys
from snet_cli.utils import type_converter


class ErrorHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: {}\n\n".format(message))
        self.print_help(sys.stderr)
        sys.exit(2)


def get_root_parser(config):
    parser = ErrorHelpParser(prog="snet", description="SingularityNET CLI")
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

    registry_p = subparsers.add_parser("registry", help="Interact with the SingularityNET Registry contract")
    add_registry_options(registry_p)

    contract_p = subparsers.add_parser("contract", help="Interact with contracts at a low level")
    add_contract_options(contract_p)


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

    p = subparsers.add_parser("endpoint", help="Switch to an endpoint-determined network")
    p.set_defaults(network_name="endpoint")
    p.set_defaults(fn="set")
    p.add_argument("endpoint", help="ethereum json-rpc endpoint (should start with 'http(s)://')", metavar="ENDPOINT")


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
    with open(Path(__file__).absolute().parent.joinpath("resources", "contracts", "Agent.json")) as f:
        contract_json = json.load(f)
        parser.set_defaults(contract_json=contract_json)

    add_contract_identity_arguments(parser, [("", "agent_at")])

    subparsers = parser.add_subparsers(title="agent commands", metavar="COMMAND")
    subparsers.required = True

    create_jobs_p = subparsers.add_parser("create-jobs", help="Create jobs")
    create_jobs_p.set_defaults(fn="create_jobs")
    create_jobs_p.set_defaults(contract_function="createJob")
    create_jobs_p.add_argument("--number", "-n", type=int, default=1, help="number of jobs to create (defaults to 1)")
    create_jobs_p.add_argument("--max-price", type=int, default=0,
                               help="skip interactive confirmation of job price if below max price (defaults to 0)")
    create_jobs_p.add_argument("--funded", action="store_true", help="fund created jobs", default=False)
    create_jobs_p.add_argument("--signed", action="store_true", help="generate job signatures for created jobs",
                               default=False)
    add_transaction_arguments(create_jobs_p)


def add_agent_factory_options(parser):
    parser.set_defaults(cmd=AgentFactoryCommand)
    with open(Path(__file__).absolute().parent.joinpath("resources", "contracts", "AgentFactory.json")) as f:
        contract_json = json.load(f)
        parser.set_defaults(contract_json=contract_json)

    add_contract_identity_arguments(parser, [("", "agent_factory_at")])

    subparsers = parser.add_subparsers(title="agent-factory commands", metavar="COMMAND")
    subparsers.required = True

    create_record_p = subparsers.add_parser("create-agent", help="Create an agent")
    create_record_p.set_defaults(fn="create_agent")
    create_record_p.set_defaults(contract_function="createAgent")
    create_record_p.add_argument("contract_named_input_price", type=type_converter("uint256"), metavar="PRICE",
                                 help="desired initial job price for agent")
    create_record_p.add_argument("contract_named_input_endpoint", type=type_converter("string"), metavar="ENDPOINT",
                                 help="initial endpoint for agebt's daemon")
    add_transaction_arguments(create_record_p)


def add_client_options(parser):
    parser.set_defaults(cmd=ClientCommand)

    subparsers = parser.add_subparsers(title="client commands", metavar="COMMAND")
    subparsers.required = True

    call_p = subparsers.add_parser("call", help="Call a service")
    call_p.set_defaults(fn="call")
    call_p.add_argument("method", help="target service's method name to call", metavar="METHOD")
    call_p.add_argument("params", help="json-serialized parameters to pass to method", metavar="PARAMS")
    call_p.add_argument("--max-price", type=int, default=0,
                        help="skip interactive confirmation of job price if below max price (defaults to 0)")
    add_contract_identity_arguments(call_p, [("agent", "agent_at"), ("job", "job_at")])
    add_transaction_arguments(call_p)


def add_registry_options(parser):
    parser.set_defaults(cmd=RegistryCommand)
    with open(Path(__file__).absolute().parent.joinpath("resources", "contracts", "Registry.json")) as f:
        contract_json = json.load(f)
        parser.set_defaults(contract_json=contract_json)

    add_contract_identity_arguments(parser, [("", "registry_at")])

    subparsers = parser.add_subparsers(title="registry commands", metavar="COMMAND")
    subparsers.required = True

    create_record_p = subparsers.add_parser("create-record", help="Create a new record")
    create_record_p.set_defaults(fn="create_record")
    create_record_p.set_defaults(contract_function="createRecord")
    create_record_p.add_argument("contract_named_input_name", type=type_converter("bytes32"), metavar="NAME",
                                 help="desired name for registry record")
    create_record_p.add_argument("contract_named_input_agent", type=type_converter("address"), metavar="AGENT_ADDRESS",
                                 help="target agent address for registry record")
    add_transaction_arguments(create_record_p)

    update_record_p = subparsers.add_parser("update-record", help="Update an existing record")
    update_record_p.set_defaults(fn="update_record")
    update_record_p.set_defaults(contract_function="updateRecord")
    update_record_p.add_argument("contract_named_input_name", type=type_converter("bytes32"), metavar="NAME",
                                 help="target name for registry record")
    update_record_p.add_argument("contract_named_input_agent", type=type_converter("address"), metavar="AGENT_ADDRESS",
                                 help="target agent address for registry record")
    add_transaction_arguments(update_record_p)

    deprecate_record_p = subparsers.add_parser("deprecate-record", help="Deprecate an existing record")
    deprecate_record_p.set_defaults(fn="deprecate_record")
    deprecate_record_p.set_defaults(contract_function="deprecateRecord")
    deprecate_record_p.add_argument("contract_named_input_name", type=type_converter("bytes32"), metavar="NAME",
                                    help="target name for registry record")
    add_transaction_arguments(deprecate_record_p)

    list_records_p = subparsers.add_parser("list-records", help="List records")
    list_records_p.set_defaults(fn="list_records")
    list_records_p.set_defaults(contract_function="listRecords")
    add_transaction_arguments(list_records_p)

    query_p = subparsers.add_parser("query", help="Query for a given name")
    query_p.set_defaults(fn="query")
    query_p.add_argument("name", type=type_converter("bytes32"), help="target name for registry record", metavar="NAME")
    add_transaction_arguments(query_p)


def add_contract_options(parser):
    parser.set_defaults(cmd=ContractCommand)

    subparsers = parser.add_subparsers(title="contracts", metavar="CONTRACT")
    subparsers.required = True

    for path in Path(__file__).absolute().parent.joinpath("resources", "contracts").glob("*json"):
        contract_name = re.search(r"([^.]*)\.json", os.path.basename(path)).group(1)
        contract_p = subparsers.add_parser(contract_name, help="{} contract".format(contract_name))
        add_contract_function_options(contract_p, contract_name)


def add_contract_function_options(parser, contract_name):
    add_contract_identity_arguments(parser)

    with open(Path(__file__).absolute().parent.joinpath("resources", "contracts",
                                                        "{}.json".format(contract_name))) as f:
        contract_json = json.load(f)
        parser.set_defaults(contract_json=contract_json)

    fns = []
    for fn in filter(lambda e: e["type"] == "function", contract_json["abi"]):
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
            metavar_name = "{}_".format(name)
        else:
            arg_name = name
            metavar_name = name
        h = "{} contract address".format(name)
        if destination != "at":
            h += " (defaults to session.default_{})".format(destination)
        identity_g.add_argument("--{}at".format(arg_name), dest=destination,
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
