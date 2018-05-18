import json
import sys
from pathlib import Path
from textwrap import indent

import jsonrpcclient
import yaml

from snet_cli.contract import Contract
from snet_cli.identity import get_kws_for_identity_type, get_identity_types
from snet_cli.session import from_config, get_session_keys
from snet_cli.utils import DefaultAttributeObject, get_web3, get_identity, serializable


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

    def get_contract_argser(self, at, contract_function, contract_json, **kwargs):
        def f(*positional_inputs, **named_inputs):
            args_dict = self.args.__dict__.copy()
            args_dict.update(dict(
                at=at,
                contract_function=contract_function,
                contract_json=contract_json,
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
                       "          Note that trezor devices currently implement a message signing scheme that is at\n"
                       "          odds with all other available tools. As such, trezor-based identities are currently\n"
                       "          only partially-functional with the snet cli (they cannot be used to call services\n"
                       "          using 'snet client')."
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
        for kw in get_kws_for_identity_type(identity_type):
            value = input("{}: \n".format(" ".join(kw.capitalize().split("_")))) or None
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

        for kw in get_kws_for_identity_type(identity_type):
            value = getattr(self.args, kw)
            self._ensure(value is not None, "--{} is required for identity_type {}".format(kw, identity_type))
            identity[kw] = value

        self.config["identity.{}".format(identity_name)] = identity
        self.config.persist()

    def list(self):
        for identity_section in filter(lambda x: x.startswith("identity."), self.config.sections()):
            identity = self.config[identity_section]
            self._pprint({identity_section[len("identity."):]: {k: v for k, v in identity.items()
                                                                if k not in ["private_key", "mnemonic"]}})

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
        self._ensure(self.config.has_section("network.{}".format(network_name)) or network_name == "endpoint",
                     "network_name {} does not exist".format(network_name))
        if network_name != "endpoint":
            for k, v in self.config["network.{}".format(network_name)].items():
                self._set_key(k, v)
        else:
            self._ensure(self.args.endpoint.startswith("http"), "endpoint must start with http")
            self._set_key("default_eth_rpc_endpoint", self.args.endpoint)


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
            self.args.at, "currentPrice", self.args.contract_json)(), None, None, self.w3, self.ident).call()
        self._set_key("current_agent_at", self.args.at, out_f=self.err_f)
        token_address = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "token", self.args.contract_json)(), None, None, self.w3, self.ident).call()
        proceed = (price <= self.args.max_price or
                   input("Accept job price {:.8f} AGI? (y/n): ".format(float(price) * 10 ** -8)) == "y")
        if proceed:
            jobs = []
            with open(Path(__file__).absolute().parent.joinpath("resources", "contracts",
                                                                "SingularityNetToken.json")) as f:
                token_contract_json = json.load(f)
            with open(Path(__file__).absolute().parent.joinpath("resources", "contracts", "Job.json")) as f:
                job_contract_json = json.load(f)
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
                        token_contract_json)(_spender=job_address, _value=price), self.err_f, self.err_f, self.w3,
                                          self.ident)
                    self._printerr("Creating transaction to approve token transfer...\n")
                    cmd.transact()
                    cmd = ContractCommand(self.config, self.get_contract_argser(
                        job_address, "fundJob",
                        job_contract_json)(), self.err_f, self.err_f, self.w3, self.ident)
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
    def call(self):
        agent_address = self._getstring("agent_at")
        self._ensure(agent_address is not None, "--agent-at is required to specify agent address")

        with open(Path(__file__).absolute().parent.joinpath("resources", "contracts", "Job.json")) as f:
            job_contract_json = json.load(f)
        with open(Path(__file__).absolute().parent.joinpath("resources", "contracts", "Agent.json")) as f:
            agent_contract_json = json.load(f)
        with open(Path(__file__).absolute().parent.joinpath("resources", "contracts",
                                                            "SingularityNetToken.json")) as f:
            token_contract_json = json.load(f)

        job_address = self._getstring("job_at")

        if job_address is not None:
            job_agent_address = ContractCommand(self.config, self.get_contract_argser(
                job_address, "agent", job_contract_json)(), None, None, self.w3, self.ident).call()
            state = ContractCommand(self.config, self.get_contract_argser(
                job_address, "state", job_contract_json)(), None, None, self.w3, self.ident).call()
            if agent_address != job_agent_address or state == 2:
                job_address = None
            else:
                price = ContractCommand(self.config, self.get_contract_argser(
                    job_address, "jobPrice", job_contract_json)(), None, None, self.w3, self.ident).call()

        if job_address is None:
            cmd = AgentCommand(self.config, self.get_contract_argser(
                None, "createJob", agent_contract_json, number=1)(), self.err_f, self.err_f, self.w3, self.ident)
            job = cmd.create_jobs()[0]
            job_address, price = job["job_address"], job["job_price"]

        self._set_key("current_job_at", job_address, out_f=self.err_f)

        token_address = ContractCommand(self.config, self.get_contract_argser(
            job_address, "token", job_contract_json)(), None, None, self.w3, self.ident).call()

        cmd = ContractCommand(self.config, self.get_contract_argser(job_address, "state", job_contract_json)(),
                              None, None, self.w3, self.ident)
        state = cmd.call()

        if state == 0:
            cmd = ContractCommand(self.config, self.get_contract_argser(
                token_address, "approve",
                token_contract_json)(_spender=job_address, _value=price), self.err_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to approve token transfer...\n")
            cmd.transact()
            cmd = ContractCommand(self.config, self.get_contract_argser(
                job_address, "fundJob",
                job_contract_json)(), self.err_f, self.err_f, self.w3, self.ident)
            self._printerr("Creating transaction to fund job...\n")
            cmd.transact()

        self._printerr("Signing job...\n")
        job_signature = self.ident.sign_message(job_address, self.err_f).hex()

        endpoint = ContractCommand(self.config, self.get_contract_argser(
            agent_address, "endpoint", agent_contract_json)(), None, None, self.w3, self.ident).call()

        params = json.loads(self._getstring("params"))

        self._printerr("Calling service...\n")

        response = jsonrpcclient.request(endpoint, self._getstring("method"),
                                         job_address=job_address, job_signature=job_signature, **params)

        self._pprint({"response": response})


class RegistryCommand(BlockchainCommand):
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
        self._pprint({"records": [{"name": names[i], "address": addresses[i]} for i in range(len(names))]})
        if self.args.at is not None:
            self._set_key("current_registry_at", self.args.at, out_f=self.err_f)

    def query(self):
        self.args.at = self._getstring("registry_at")
        index = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "agentIndex", self.args.contract_json)(self.args.name), None, None, self.w3,
                                self.ident).call()
        record = ContractCommand(self.config, self.get_contract_argser(
            self.args.at, "agentRecords", self.args.contract_json)(index), None, None, self.w3, self.ident).call()
        self._pprint({"record": {"agent": record[0], "name": record[1].partition(b"\0")[0].decode("utf-8"),
                     "state": record[2]}})
        self._set_key("current_agent_at", record[0], out_f=self.err_f)
        if self.args.at is not None:
            self._set_key("current_registry_at", self.args.at, out_f=self.err_f)


class ContractCommand(BlockchainCommand):
    def call(self):
        contract_address = self._getstring("at")

        if contract_address is None:
            networks = self.args.contract_json["networks"]
            chain_id = self.w3.version.network
            contract_address = networks.get(chain_id, {}).get("address", None)

        self._ensure(contract_address is not None, "--at is required to specify target contract address")

        abi = self.args.contract_json["abi"]

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
            networks = self.args.contract_json["networks"]
            chain_id = self.w3.version.network
            contract_address = networks.get(chain_id, {}).get("address", None)

        self._ensure(contract_address is not None, "--at is required to specify target contract address")

        abi = self.args.contract_json["abi"]

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
