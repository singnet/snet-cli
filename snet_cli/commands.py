import json
import sys
import os
import shlex
import tarfile
import tempfile
from pathlib import Path
from textwrap import indent
from urllib.parse import urljoin, urlparse
from rfc3986 import urlparse, uri_reference

import jsonrpcclient
import yaml
import getpass
import ipfsapi

from snet_cli.contract import Contract
from snet_cli.identity import get_kws_for_identity_type, get_identity_types
from snet_cli.session import from_config, get_session_keys
from snet_cli.utils import DefaultAttributeObject, get_web3, get_identity, serializable, walk_imports, \
                           read_temp_tar, type_converter, get_contract_dict


class Command(object):
    def __init__(self, config, args, out_f=sys.stdout, err_f=sys.stderr):
        self.config = config
        self.session = from_config(self.config)
        self.args = args
        self.out_f = out_f
        self.err_f = err_f
        if self.config.getboolean("session", "init", fallback=False):
            del self.config["session"]["init"]
            InitCommand(self.config, None, self.out_f, self.err_f).init()
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

    def _set_key(self, key, value, config=None, out_f=None, err_f=None):
        SessionCommand(config or self.config, DefaultAttributeObject(key=key, value=value), out_f or self.out_f,
                       err_f or self.err_f).set()

    def _nothing(self):
        pass


class BlockchainCommand(Command):
    def __init__(self, config, args, out_f=sys.stdout, err_f=sys.stderr, w3=None, ident=None):
        super(BlockchainCommand, self).__init__(config, args, out_f, err_f)
        self.w3 = w3 or get_web3(self._getstring("eth_rpc_endpoint"))
        self.ident = ident or get_identity(self.w3, self.session, self.args)

    def get_contract_argser(self, at, contract_function, contract_dict, **kwargs):
        def f(*positional_inputs, **named_inputs):
            args_dict = self.args.__dict__.copy()
            args_dict.update(dict(
                at=at,
                contract_function=contract_function,
                contract_dict=contract_dict,
                contract_positional_inputs=positional_inputs,
                **kwargs
            ))
            for k, v in named_inputs.items():
                args_dict["contract_named_input_{}".format(k)] = v
            return DefaultAttributeObject(**args_dict)
        return f


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
        identity_name = input("Choose a name for your first identity: \n") or None
        self._ensure(identity_name is not None, "identity name is required")
        create_identity_kwargs["identity_name"] = identity_name
        identity_type = input("Select an identity type for your first identity (choose from {}): \n".format(
            get_identity_types())) or None
        self._ensure(identity_type in get_identity_types(),
                     "identity type {} not in {}".format(identity_type, get_identity_types()))
        create_identity_kwargs["identity_type"] = identity_type
        for kw, is_secret in get_kws_for_identity_type(identity_type):
            kw_prompt = "{}: \n".format(" ".join(kw.capitalize().split("_")))
            if is_secret:
                value = getpass.getpass(kw_prompt) or None
            else:
                value = input(kw_prompt) or None
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


class AgentCommand(BlockchainCommand):
    def create_jobs(self):
        self.args.at = self._getstring("agent_at")
        self._ensure(self.args.at is not None, "--at is required to specify agent contract address")
        price = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "currentPrice", self.args.contract_dict)(), None, None, self.w3, self.ident).call()
        self._set_key("current_agent_at", self.args.at, out_f=self.err_f)
        token_address = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "token", self.args.contract_dict)(), None, None, self.w3, self.ident).call()
        proceed = (price <= self.args.max_price or
                   input("Accept job price {:.8f} AGI? (y/n): ".format(float(price) * 10 ** -8)) == "y")
        if proceed:
            jobs = []
            token_contract_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "SingularityNetToken")
            job_contract_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "Job")
            for _ in range(self.args.number):
                job = {"job_price": price}
                cmd = ContractCommand(self.config, self.args, self.err_f, self.err_f, self.w3, self.ident)
                self._printerr("Creating transaction to create job...\n")
                _, events = cmd.transact()
                if events[0].args.jobPrice > price:
                    self._printerr("agent's currentPrice increased while creating jobs\n")
                    break
                job_address = events[0].args.job
                job["job_address"] = job_address
                self._set_key("current_job_at", job_address, out_f=self.err_f)
                self.session = from_config(self.config)
                if self.args.funded:
                    cmd = ContractCommand(self.config, self.get_contract_argser(
                        token_address, "approve",
                        token_contract_dict)(_spender=job_address, _value=price), self.err_f, self.err_f, self.w3,
                                          self.ident)
                    self._printerr("Creating transaction to approve token transfer...\n")
                    cmd.transact()
                    cmd = ContractCommand(self.config, self.get_contract_argser(
                        job_address, "fundJob",
                        job_contract_dict)(), self.err_f, self.err_f, self.w3, self.ident)
                    self._printerr("Creating transaction to fund job...\n")
                    cmd.transact()
                if self.args.signed:
                    self._printerr("Signing job...\n")
                    job["job_signature"] = self.ident.sign_message(job_address, self.err_f).hex()
                jobs.append(job)
            self._pprint({"jobs": jobs})

            return jobs
        else:
            self._error("Cancelled")


class AgentFactoryCommand(BlockchainCommand):
    def create_agent(self):
        self.args.at = self._getstring("agent_factory_at")
        cmd = ContractCommand(self.config, self.args, self.out_f, self.err_f, self.w3, self.ident)
        self._printerr("Creating transaction to create agent...\n")
        _, events = cmd.transact()
        self._set_key("current_agent_at", events[0].args.agent, out_f=self.err_f)
        if self.args.at is not None:
            self._set_key("current_agent_factory_at", self.args.at, out_f=self.err_f)


class ClientCommand(BlockchainCommand):

    def _get_call_params(self, args):
        # Don't use _get_string because it doesn't make sense to store this with session/identity.
        # We also want to fall back to stdin or a file
        params_string = getattr(args, "params", None)

        if params_string is None or params_string == "-":
            params_source = "stdin"
            self._printerr("Waiting for call params on stdin...\n")
            params_string = sys.stdin.read()
        elif Path(params_string).is_file():
            params_source = "file"
            fn = params_string
            with open(fn, 'rb') as f:
                params_string = f.read()
        else:
            params_source = "cmdline"

        params = json.loads(params_string)

        return params_source, params

    def call(self):
        agent_address = self._getstring("agent_at")
        self._ensure(agent_address is not None, "--agent-at is required to specify agent address")

        job_contract_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "Job")
        agent_contract_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "Agent")
        token_contract_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "SingularityNetToken")

        job_address = self._getstring("job_at")

        if job_address is not None:
            job_agent_address = ContractCommand(self.config, self.get_contract_argser(
                job_address, "agent", job_contract_dict)(), None, None, self.w3, self.ident).call()
            state = ContractCommand(self.config, self.get_contract_argser(
                job_address, "state", job_contract_dict)(), None, None, self.w3, self.ident).call()
            if agent_address != job_agent_address or state == 2:
                job_address = None
            else:
                price = ContractCommand(self.config, self.get_contract_argser(
                    job_address, "jobPrice", job_contract_dict)(), None, None, self.w3, self.ident).call()

        if job_address is None:
            cmd = AgentCommand(self.config, self.get_contract_argser(
                None, "createJob", agent_contract_dict, number=1)(), self.err_f, self.err_f, self.w3, self.ident)
            job = cmd.create_jobs()[0]
            job_address, price = job["job_address"], job["job_price"]

        self._set_key("current_job_at", job_address, out_f=self.err_f)

        token_address = ContractCommand(self.config, self.get_contract_argser(
            job_address, "token", job_contract_dict)(), None, None, self.w3, self.ident).call()

        cmd = ContractCommand(self.config, self.get_contract_argser(job_address, "state", job_contract_dict)(),
                              None, None, self.w3, self.ident)
        state = cmd.call()

        if state == 0:
            cmd = ContractCommand(self.config, self.get_contract_argser(
                token_address, "approve",
                token_contract_dict)(_spender=job_address, _value=price), self.err_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to approve token transfer...\n")
            cmd.transact()
            cmd = ContractCommand(self.config, self.get_contract_argser(
                job_address, "fundJob",
                job_contract_dict)(), self.err_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to fund job...\n")
            cmd.transact()

        self._printerr("Signing job...\n")
        job_signature = self.ident.sign_message(job_address, self.err_f).hex()

        endpoint = ContractCommand(self.config, self.get_contract_argser(
            agent_address, "endpoint", agent_contract_dict)(), None, None, self.w3, self.ident).call()

        params_source, params = self._get_call_params(self.args)

        self._printerr("Read call params from {}...\n".format(params_source))

        self._printerr("Calling service...\n")

        response = jsonrpcclient.request(endpoint, self._getstring("method"),
                                         job_address=job_address, job_signature=job_signature, **params)

        self._pprint({"response": response})


class RegistryCommand(BlockchainCommand):
    # Warning: none of these commands work with the new Registry
    def create_record(self):
        self.args.at = self._getstring("registry_at")
        cmd = ContractCommand(self.config, self.args, self.out_f, self.err_f, self.w3, self.ident)
        self._printerr("Creating transaction to create record...\n")
        cmd.transact()
        if self.args.at is not None:
            self._set_key("current_registry_at", self.args.at, out_f=self.err_f)

    def update_record(self):
        self.args.at = self._getstring("registry_at")
        cmd = ContractCommand(self.config, self.args, self.out_f, self.err_f, self.w3, self.ident)
        self._printerr("Creating transaction to update record...\n")
        cmd.transact()
        if self.args.at is not None:
            self._set_key("current_registry_at", self.args.at, out_f=self.err_f)

    def deprecate_record(self):
        self.args.at = self._getstring("registry_at")
        cmd = ContractCommand(self.config, self.args, self.out_f, self.err_f, self.w3, self.ident)
        self._printerr("Creating transaction to deprecate record...\n")
        cmd.transact()
        if self.args.at is not None:
            self._set_key("current_registry_at", self.args.at, out_f=self.err_f)

    def list_records(self):
        self.args.at = self._getstring("registry_at")
        [names, addresses] = ContractCommand(self.config, self.args, None, None, self.w3, self.ident).call()
        names = list(map(lambda n: n.partition(b"\0")[0].decode("utf-8"), names))
        records = [{"name": names[i], "address": addresses[i]} for i 
            in range(len(names)) 
            if names[i] != ""
                and addresses[i] != "0x0000000000000000000000000000000000000000"]
        self._pprint({"records": records})
        if self.args.at is not None:
            self._set_key("current_registry_at", self.args.at, out_f=self.err_f)

    def query(self):
        self.args.at = self._getstring("registry_at")
        index = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "agentIndex", self.args.contract_dict)(self.args.name), None, None, self.w3,
                                self.ident).call()
        record = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "agentRecords", self.args.contract_dict)(index), None, None, self.w3, self.ident).call()
        self._pprint({"record": {"agent": record[0], "name": record[1].partition(b"\0")[0].decode("utf-8"),
                     "state": record[2]}})
        self._set_key("current_agent_at", record[0], out_f=self.err_f)
        if self.args.at is not None:
            self._set_key("current_registry_at", self.args.at, out_f=self.err_f)


class ContractCommand(BlockchainCommand):
    def call(self):
        contract_address = self._getstring("at")

        if contract_address is None:
            networks = self.args.contract_dict["networks"]
            chain_id = self.w3.version.network
            contract_address = networks.get(chain_id, {}).get("address", None)

        self._ensure(contract_address is not None, "--at is required to specify target contract address")

        abi = self.args.contract_dict["abi"]

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
            networks = self.args.contract_dict["networks"]
            chain_id = self.w3.version.network
            contract_address = networks.get(chain_id, {}).get("address", None)

        self._ensure(contract_address is not None, "--at is required to specify target contract address")

        abi = self.args.contract_dict["abi"]

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

        if not self.args.no_confirm or self.args.verbose:
            self._pprint({"transaction": txn})

        proceed = self.args.no_confirm or input("Proceed? (y/n): ") == "y"

        if proceed:
            receipt = self.ident.transact(txn, self.err_f)
            events = contract.process_receipt(receipt)
            self._pprint_receipt_and_events(receipt, events)
            return receipt, events
        else:
            self._error("Cancelled")


class ServiceCommand(BlockchainCommand):

    # We are sorting files before we add them to the .tar since an archive containing the same files in a different
    # order will produce a different content hash; sorting order is the same default sorting order used in GNU tar.
    def _tar_imports(self, paths, entry_path):
        paths = sorted(paths, key=lambda unsorted_path: (len(unsorted_path.parts), str(unsorted_path.name)))
        f = tempfile.NamedTemporaryFile()
        tar = tarfile.open(fileobj=f, mode="w")
        for path in paths:
            tar.add(path, path.relative_to(entry_path))
            self._printout("path: {}".format(str(path)))

        tar.close()
        return f

    def _get_network(self):
        if "network_name" in self.args and self.args.network_name:
            if "eth_rpc_endpoint" in self.args and self.args.eth_rpc_endpoint:
                network = self.args.eth_rpc_endpoint
            else:
                network = self.config["network.{}".format(self.args.network)]['default_eth_rpc_endpoint']
            self.w3 = get_web3(network)
        return self.w3.version.network

    def init(self):
        accept_all_defaults = self.args.y
        init_args = {
            "name": os.path.basename(os.getcwd()),
            "model": "model/",
            "organization": "",
            "path": "",
            "price": 0,
            "endpoint": "",
            "tags": [],
            "metadata": {
                "description": ""
            }
        }

        if not accept_all_defaults:
            self._printout("Please provide values to populate your service.json file\n")

        if self.args.name:
            init_args["name"] = self.args.name
        elif not accept_all_defaults:
            init_args["name"] = input('Choose a name for your service: (default: "{}")\n'.format(init_args["name"])) or init_args["name"]

        if self.args.model:
            init_args["model"] = self.args.model
        elif not accept_all_defaults:
            init_args["model"] = input('Choose the path to your service\'s model directory: (default: "{}")\n'.format(init_args["model"])) or init_args["model"]

        if self.args.organization:
            init_args["organization"] = self.args.organization
        elif not accept_all_defaults:
            init_args["organization"] = input('Choose an organization to register your service under: (default: "{}")\n'.format(init_args["organization"])) or init_args["organization"]

        if self.args.path:
            init_args["path"] = self.args.path
        elif not accept_all_defaults:
            init_args["path"] = input('Choose the path under which your Service registration will be created: (default: "{}")\n'.format(init_args["path"])) or init_args["path"]

        if self.args.price:
            init_args["price"] = self.args.price
        elif not accept_all_defaults:
            init_args["price"] = input('Choose a price in AGI to call your service: (default: {})\n'.format(init_args["price"])) or init_args["price"]

        if self.args.endpoint:
            init_args["endpoint"] = self.args.endpoint
        elif not accept_all_defaults:
            init_args["endpoint"] = input('Endpoint to call the API for your service: (default: "{}")\n'.format(init_args["endpoint"])) or init_args["endpoint"]

        if self.args.tags:
            init_args["tags"] = self.args.tags
        elif not accept_all_defaults:
            init_args["tags"] = shlex.split(input("Input a list of tags for your service: (default: {})\n".format(init_args["tags"])) or init_args["tags"])

        if self.args.description:
            init_args["metadata"]["description"] = self.args.description
        elif not accept_all_defaults:
            init_args["metadata"]["description"] = input('Input a description for your service: (default: "{}")\n'.format(init_args["metadata"]["description"])) or init_args["metadata"]["description"]

        with open("service.json", "w") as f:
            json.dump(init_args, f, indent=4, ensure_ascii=False)
        self._printout(json.dumps(init_args, indent=4, sort_keys=True))
        self._printout("\nservice.json file has been created!")

    def publish(self):
        network = self._get_network()

        if "config" in self.args and self.args.config:
            service_json_path = self.args.config
        else:
            service_json_path = "service.json"

        with open(service_json_path) as f:
            service_json = json.load(f)

        if service_json.get('networks', {}).get(self.w3.version.network, {}).get('agentAddress', {}):
            self._error("Service has already been deployed to network with id {}".format(network))

        # Get list of model files
        import_paths = None
        if 'model' in service_json and service_json['model']:
            model_path = Path(service_json['model'])
            if not os.path.isabs(model_path):
                entry_path = Path.cwd().joinpath(model_path).resolve()
            else:
                entry_path = model_path.resolve()
            if not os.path.isdir(entry_path):
                self._error("Model path must resolve to a valid directory: {}".format(model_path))
            import_paths = walk_imports(entry_path)

        # Create model tar and upload it to IPFS
        ipfs_endpoint = urlparse(self.config["ipfs"]["default_ipfs_endpoint"])
        ipfs_scheme = ipfs_endpoint.scheme if ipfs_endpoint.scheme else "http"
        ipfs_port = ipfs_endpoint.port if ipfs_endpoint.port else 5001
        ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_endpoint.hostname), ipfs_port)
        model_ipfs_uri = None

        if import_paths:
            tmp_f = self._tar_imports(import_paths, entry_path)
            model_ipfs_hash = ipfs_client.add(read_temp_tar(tmp_f).name)["Hash"]
            model_ipfs_path = "/ipfs/{}".format(model_ipfs_hash)
            model_ipfs_uri = uri_reference(model_ipfs_path).copy_with(scheme='ipfs').unsplit()

        # Upload metadata JSON to IPFS with modelURI
        metadata_json = dict(service_json['metadata'])

        if model_ipfs_uri:
            metadata_json['modelURI'] = model_ipfs_uri

        with tempfile.NamedTemporaryFile(mode='w+') as tmp_json:
            json.dump(metadata_json, tmp_json)
            tmp_json.seek(0)
            metadata_ipfs_hash = ipfs_client.add(tmp_json.name)["Hash"]
        metadata_ipfs_path = "/ipfs/{}".format(metadata_ipfs_hash)
        metadata_ipfs_uri = uri_reference(metadata_ipfs_path).copy_with(scheme='ipfs').unsplit()

        # Create Agent
        agent_factory_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "AgentFactory")
        self.args.at = self._getstring("agent_factory_at")
        cmd = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "createAgent", agent_factory_dict)(
                type_converter('uint256')(service_json['price']), service_json['endpoint'], metadata_ipfs_uri
            ), self.out_f, self.err_f, self.w3, self.ident)
        self._printerr("Creating transaction to create agent...\n")
        _, events = cmd.transact()

        # Update service.json with Agent address
        agent_address = events[0].args.agent
        if "networks" not in service_json:
            service_json['networks'] = {}
        service_json['networks'][self.w3.version.network] = {
            "agentAddress": agent_address
        }
        self._printerr("Adding contract address to service.json file...\n")
        with open(service_json_path, "w+") as f:
            json.dump(service_json, f, indent=4, ensure_ascii=False)

        # Register Agent
        if not self.args.no_register:
            registry_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "Registry")
            self.args.at = self._getstring("registry_at")
            cmd = ContractCommand(self.config, self.get_contract_argser(
                self.args.at, "createServiceRegistration", registry_dict)(
                    type_converter('bytes32')(service_json['organization']),
                    type_converter('bytes32')(service_json['name']),
                    type_converter('bytes32')(service_json['path']),
                    type_converter('address')(agent_address),
                    list(map(type_converter('bytes32'), service_json['tags']))
                ), self.out_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to create record...\n")
            cmd.transact()

    def update(self):
        network = self._get_network()

        if "config" in self.args and self.args.config:
            service_json_path = self.args.config
        else:
            service_json_path = "service.json"

        with open(service_json_path) as f:
            service_json = json.load(f)

        agent_contract_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "Agent")

        if not service_json.get('networks', {}).get(self.w3.version.network, {}).get('agentAddress', {}):
            self._error("Service hasn't been deployed to network with id {}".format(network))

        if self.args.new_price:
            cmd = ContractCommand(self.config, self.get_contract_argser(
                service_json['networks'][self.w3.version.network]['agentAddress'], "setPrice", agent_contract_dict)(
                self.args.new_price
            ), self.out_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to update price...\n")
            cmd.transact()

        if self.args.new_endpoint:
            cmd = ContractCommand(self.config, self.get_contract_argser(
                service_json['networks'][self.w3.version.network]['agentAddress'], "setEndpoint", agent_contract_dict)(
                self.args.new_endpoint
            ), self.out_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to update endpoint...\n")
            cmd.transact()

        if self.args.new_description:
            # Get current metadata JSON
            cmd = ContractCommand(self.config, self.get_contract_argser(
                service_json['networks'][self.w3.version.network]['agentAddress'], "metadataURI",
                agent_contract_dict)(), self.out_f, self.err_f, self.w3, self.ident
            )
            metadata_uri = cmd.call()
            ipfs_endpoint = urlparse(self.config["ipfs"]["default_ipfs_endpoint"])
            ipfs_scheme = ipfs_endpoint.scheme if ipfs_endpoint.scheme else "http"
            ipfs_port = ipfs_endpoint.port if ipfs_endpoint.port else 5001
            ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_endpoint.hostname), ipfs_port)
            ipfs_client.get(urlparse(metadata_uri).path)
            ipfs_file_path = Path.cwd().joinpath(urlparse(metadata_uri).path.split("/")[-1])
            with open(ipfs_file_path) as f:
                metadata_json = json.load(f)
            os.remove(ipfs_file_path)

            # Create new metadata JSON tmp file with updated description
            metadata_json['description'] = self.args.new_description
            with tempfile.NamedTemporaryFile(mode='w+') as tmp_json:
                json.dump(metadata_json, tmp_json, indent=4, ensure_ascii=False)
                tmp_json.seek(0)
                metadata_ipfs_hash = ipfs_client.add(tmp_json.name)["Hash"]

            # Update metadataURI in the contract
            metadata_ipfs_path = "/ipfs/{}".format(metadata_ipfs_hash)
            metadata_ipfs_uri = uri_reference(metadata_ipfs_path).copy_with(scheme='ipfs').unsplit()
            cmd = ContractCommand(self.config, self.get_contract_argser(
                service_json['networks'][self.w3.version.network]["agentAddress"], "setMetadataURI", agent_contract_dict)(metadata_ipfs_uri), self.out_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to update metadataURI...\n")
            cmd.transact()

        if self.args.add_tags:
            registry_contract_dict = get_contract_dict(Path(__file__).absolute().parent.joinpath("resources", "contracts"), "Registry")
            cmd = ContractCommand(self.config, self.get_contract_argser(
                registry_contract_dict['networks'][self.w3.version.network]['address'], "addTagsToServiceRegistration", registry_contract_dict
            )(
                type_converter('bytes32')(service_json['organization']),
                type_converter('bytes32')(service_json['name']),
                self.args.add_tags
            ), self.out_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to add tags...\n")
            cmd.transact()