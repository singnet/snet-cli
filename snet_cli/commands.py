import getpass
import io
import json
import os
import shlex
import sys
import tarfile
import tempfile
from pathlib import Path
from textwrap import indent
from urllib.parse import urljoin, urlparse

import grpc
import ipfsapi
import pkg_resources
import requests
import yaml
from google.protobuf import json_format
from grpc_tools.protoc import main as protoc
from rfc3986 import urlparse, uri_reference

from snet_cli.contract import Contract
from snet_cli.identity import get_kws_for_identity_type, get_identity_types
from snet_cli.session import from_config, get_session_keys
from snet_cli.utils import DefaultAttributeObject, get_web3, get_identity, serializable, walk_imports, \
    read_temp_tar, type_converter, get_contract_def, get_agent_version


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

    def _set_key(self, key, value, config=None, out_f=None, err_f=None):
        SessionCommand(config or self.config, DefaultAttributeObject(key=key, value=value), out_f or self.out_f,
                       err_f or self.err_f).set()

    def _unset_key(self, key, config=None, out_f=None, err_f=None):
        SessionCommand(config or self.config, DefaultAttributeObject(key=key), out_f or self.out_f,
                       err_f or self.err_f).unset()

    def _nothing(self):
        pass


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


class AgentCommand(BlockchainCommand):
    def create_jobs(self):
        agent_contract_def = get_contract_def("Agent")
        agent_address = self._getstring("agent_at")
        self._ensure(agent_address is not None, "--at is required to specify agent contract address")
        price = ContractCommand(
            config=self.config,
            args=self.get_contract_argser(
                contract_address=agent_address,
                contract_function="currentPrice",
                contract_def=agent_contract_def)(),
            out_f=None,
            err_f=None,
            w3=self.w3,
            ident=self.ident).call()
        self._set_key("current_agent_at", agent_address, out_f=self.err_f)
        token_address = ContractCommand(
            config=self.config,
            args=self.get_contract_argser(
                contract_address=agent_address,
                contract_function="token",
                contract_def=agent_contract_def)(),
            out_f=None,
            err_f=None,
            w3=self.w3,
            ident=self.ident).call()
        proceed = (price <= self.args.max_price or
                   input("Accept job price {:.8f} AGI? (y/n): ".format(float(price) * 10 ** -8)) == "y")
        if proceed:
            jobs = []
            token_contract_def = get_contract_def("SingularityNetToken")
            job_contract_def = get_contract_def("Job")
            for _ in range(self.args.number):
                job = {"job_price": price}
                cmd = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=agent_address,
                        contract_function="createJob",
                        contract_def=agent_contract_def)(),
                    out_f=self.err_f,
                    err_f=self.err_f,
                    w3=self.w3,
                    ident=self.ident)
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
                    cmd = ContractCommand(
                        config=self.config,
                        args=self.get_contract_argser(
                            contract_address=token_address,
                            contract_function="approve",
                            contract_def=token_contract_def)(job_address, price),
                        out_f=self.err_f,
                        err_f=self.err_f,
                        w3=self.w3,
                        ident=self.ident)
                    self._printerr("Creating transaction to approve token transfer...\n")
                    cmd.transact()
                    cmd = ContractCommand(
                        config=self.config,
                        args=self.get_contract_argser(
                            contract_address=job_address,
                            contract_function="fundJob",
                            contract_def=job_contract_def)(),
                        out_f=self.err_f,
                        err_f=self.err_f,
                        w3=self.w3,
                        ident=self.ident)
                    self._printerr("Creating transaction to fund job...\n")
                    cmd.transact()
                if self.args.signed:
                    self._printerr("Signing job...\n")
                    job["job_signature"] = self.ident.sign_message(
                        job_address, self.err_f, agent_version=get_agent_version(self.w3, agent_address)).hex()
                jobs.append(job)
            self._pprint({"jobs": jobs})

            return jobs
        else:
            self._error("Cancelled")


class AgentFactoryCommand(BlockchainCommand):
    def create_agent(self):
        agent_factory_contract_def = get_contract_def("AgentFactory")
        agent_factory_address = self._getstring("agent_factory_at")
        cmd = ContractCommand(
            config=self.config,
            args=self.get_contract_argser(
                contract_address=agent_factory_address,
                contract_function="createAgent",
                contract_def=agent_factory_contract_def)(),
            out_f=self.out_f,
            err_f=self.err_f,
            w3=self.w3,
            ident=self.ident)
        self._printerr("Creating transaction to create agent...\n")
        _, events = cmd.transact()
        self._set_key("current_agent_at", events[0].args.agent, out_f=self.err_f)
        if agent_factory_address is not None:
            self._set_key("current_agent_factory_at", agent_factory_address, out_f=self.err_f)


class ClientCommand(BlockchainCommand):

    def _get_call_params(self, args):
        # Don't use _get_string because it doesn't make sense to store this with session/identity.
        # We also want to fall back to stdin or a file
        params_string = getattr(args, "params", None)

        params_source = "cmdline"

        try:
            if Path(params_string).is_file():
                params_source = "file"
                fn = params_string
                with open(fn, 'rb') as f:
                    params_string = f.read()
        except OSError:
            if params_string is None or params_string == "-":
                params_source = "stdin"
                self._printerr("Waiting for call params on stdin...\n")
                params_string = sys.stdin.read()

        params = json.loads(params_string)

        return params_source, params

    def get_model(self):
        agent_address = self._getstring("agent_at")
        self._ensure(agent_address is not None, "--agent-at is required to specify agent address")

        agent_contract_def = get_contract_def("Agent")

        metadata_uri = ContractCommand(
            config=self.config,
            args=self.get_contract_argser(
                contract_address=agent_address,
                contract_function="metadataURI",
                contract_def=agent_contract_def)(),
            out_f=None,
            err_f=None,
            w3=self.w3,
            ident=self.ident).call()

        self._ensure(metadata_uri is not None and metadata_uri != "", "agent does not have valid metadataURI")

        try:
            ipfs_endpoint = urlparse(self.config["ipfs"]["default_ipfs_endpoint"])
            ipfs_scheme = ipfs_endpoint.scheme if ipfs_endpoint.scheme else "http"
            ipfs_port = ipfs_endpoint.port if ipfs_endpoint.port else 5001
            ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_endpoint.hostname), ipfs_port)
            model_hash = json.loads(ipfs_client.cat(metadata_uri.split("/")[-1]))["modelURI"].split("/")[-1]

            model_dir = self._getstring("dest_dir") or Path("~").expanduser().joinpath(".snet").joinpath("models").joinpath(model_hash)
            if not os.path.exists(model_dir):
                os.makedirs(model_dir)
                model_tar = ipfs_client.cat(model_hash)
                with tarfile.open(fileobj=io.BytesIO(model_tar)) as f:
                    f.extractall(model_dir)
            self._pprint({"destination": str(model_dir)})
            return model_hash
        except Exception as e:
            self._error("failed to retrieve service model")

    def call(self):
        agent_address = self._getstring("agent_at")
        self._ensure(agent_address is not None, "--agent-at is required to specify agent address")

        job_contract_def = get_contract_def("Job")
        agent_contract_def = get_contract_def("Agent")
        token_contract_def = get_contract_def("SingularityNetToken")

        job_address = self._getstring("job_at")

        if job_address is not None:
            job_agent_address = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=job_address,
                    contract_function="agent",
                    contract_def=job_contract_def)(),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()
            state = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=job_address,
                    contract_function="state",
                    contract_def=job_contract_def)(),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()
            if agent_address != job_agent_address or state == 2:
                job_address = None
            else:
                price = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=job_address,
                        contract_function="jobPrice",
                        contract_def=job_contract_def)(),
                    out_f=None,
                    err_f=None,
                    w3=self.w3,
                    ident=self.ident).call()

        model_hash = ClientCommand(
            config=self.config,
            args=self.args,
            out_f=None,
            err_f=None,
            w3=self.w3,
            ident=self.ident).get_model()

        model_dir = Path("~").expanduser().joinpath(".snet").joinpath("models").joinpath(model_hash)

        try:
            codegen_dir = Path("~").expanduser().joinpath(".snet").joinpath("py-codegen").joinpath(model_hash)
            if not os.path.exists(codegen_dir):
                os.makedirs(codegen_dir)
                proto_include = pkg_resources.resource_filename('grpc_tools', '_proto')
                protoc_args = [
                    "protoc",
                    "-I{}".format(model_dir),
                    '-I{}'.format(proto_include),
                    "--python_out={}".format(codegen_dir),
                    "--grpc_python_out={}".format(codegen_dir)
                ]
                protoc_args.extend([str(p) for p in model_dir.glob("**/*.proto")])
                protoc(protoc_args)

            sys.path.append(str(codegen_dir))
            mods = []
            for p in codegen_dir.glob("*_pb2*"):
                m = __import__(p.name.replace(".py", ""))
                mods.append(m)

            method = self._getstring("method")

            service_name = None
            request_name = None
            response_name = None
            need_break = False
            for mod in mods:
                if need_break:
                    break
                desc = getattr(mod, "DESCRIPTOR", None)
                if desc is not None:
                    for s_name, s_desc in desc.services_by_name.items():
                        if need_break:
                            break
                        for m_desc in s_desc.methods:
                            if need_break:
                                break
                            if m_desc.name == method:
                                service_name = s_name
                                request_name = m_desc.input_type.name
                                response_name = m_desc.output_type.name
                                need_break = True

            self._ensure(None not in [service_name, request_name, response_name], "failed to load service model")

            stub_class = None
            request_class = None
            response_class = None
            for mod in mods:
                if stub_class is None:
                    stub_class = getattr(mod, service_name + "Stub", None)
                if request_class is None:
                    request_class = getattr(mod, request_name, None)
                if response_class is None:
                    response_class = getattr(mod, response_name, None)

            self._ensure(None not in [stub_class, request_class, response_class], "failed to load service model")
        except Exception as e:
            self._error("failed to load service model")

        if job_address is None:
            cmd = AgentCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=None,
                    contract_function="createJob",
                    contract_def=agent_contract_def,
                    number=1)(),
                out_f=self.err_f,
                err_f=self.err_f,
                w3=self.w3,
                ident=self.ident)
            job = cmd.create_jobs()[0]
            job_address, price = job["job_address"], job["job_price"]

        self._set_key("current_job_at", job_address, out_f=self.err_f)

        token_address = ContractCommand(
            config=self.config,
            args=self.get_contract_argser(
                contract_address=job_address,
                contract_function="token",
                contract_def=job_contract_def)(),
            out_f=None,
            err_f=None,
            w3=self.w3,
            ident=self.ident).call()

        state = ContractCommand(
            config=self.config,
            args=self.get_contract_argser(
                contract_address=job_address,
                contract_function="state",
                contract_def=job_contract_def)(),
            out_f=None,
            err_f=None,
            w3=self.w3,
            ident=self.ident).call()

        if state == 0:
            cmd = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=token_address,
                    contract_function="approve",
                    contract_def=token_contract_def)(job_address, price),
                out_f=self.err_f,
                err_f=self.err_f,
                w3=self.w3,
                ident=self.ident)
            self._printerr("Creating transaction to approve token transfer...\n")
            cmd.transact()
            cmd = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=job_address,
                    contract_function="fundJob",
                    contract_def=job_contract_def)(),
                out_f=self.err_f,
                err_f=self.err_f,
                w3=self.w3,
                ident=self.ident)
            self._printerr("Creating transaction to fund job...\n")
            cmd.transact()

        agent_version = get_agent_version(self.w3, agent_address)

        self._printerr("Signing job...\n")
        job_signature = self.ident.sign_message(job_address, self.err_f, agent_version=agent_version).hex()

        endpoint = ContractCommand(
            config=self.config,
            args=self.get_contract_argser(
                contract_address=agent_address,
                contract_function="endpoint",
                contract_def=agent_contract_def)(),
            out_f=None,
            err_f=None,
            w3=self.w3,
            ident=self.ident).call()

        channel = grpc.insecure_channel(endpoint.replace("https://", "", 1).replace("http://", "", 1))

        stub = stub_class(channel)
        call_fn = getattr(stub, method)

        params_source, params = self._get_call_params(self.args)

        self._printerr("Read call params from {}...\n".format(params_source))

        request = request_class()
        json_format.Parse(json.dumps(params), request, True)

        encoding = requests.get(endpoint + "/encoding").text.strip()

        if encoding == "json":
            def json_serializer(*args, **kwargs):
                return bytes(json_format.MessageToJson(args[0], True, preserving_proto_field_name=True), "utf-8")

            def json_deserializer(*args, **kwargs):
                resp = response_class()
                json_format.Parse(args[0], resp, True)
                return resp

            call_fn._request_serializer = json_serializer
            call_fn._response_deserializer = json_deserializer

        self._printerr("Calling service...\n")

        response = call_fn(request, metadata=[("snet-job-address", job_address), ("snet-job-signature", job_signature)])

        self._pprint({"response": json.loads(json_format.MessageToJson(response, True, preserving_proto_field_name=True))})


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

        tar.close()
        return f

    def _get_network(self):
        if "network_name" in self.args and self.args.network_name:
            if "eth_rpc_endpoint" in self.args and self.args.eth_rpc_endpoint:
                network = self.args.eth_rpc_endpoint
            else:
                network = self.config["network.{}".format(self.args.network_name)]['default_eth_rpc_endpoint']
            self.w3 = get_web3(network)
        return self.w3.version.network

    def _getserviceregistrationbyname(self, service_json=None):
        try:
            if service_json:
                organization = service_json["organization"]
                service_name = service_json["name"]
            elif self.args.organization and self.args.name:
                    organization = self.args.organization
                    service_name = self.args.name
            else:
                self._error("Fail to get ORG_NAME and SERVICE_NAME...")

            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")

            return ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=registry_address,
                    contract_function="getServiceRegistrationByName",
                    contract_def=registry_contract_def)(type_converter("bytes32")(organization),
                                                        type_converter("bytes32")(service_name)),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()

        except Exception as e:
            self._printerr("\nCall getServiceRegistrationByName() error!\nHINT: Check your identity and session.\n")
            self._error(e)

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
            init_args["price"] = int(input('Choose a price in AGI to call your service: (default: {})\n'.format(init_args["price"])) or init_args["price"])

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
        self._printout(json.dumps(init_args, indent=4))
        self._printout("\nservice.json file has been created!")

    def publish(self):
        network_id = self._get_network()

        if "config" in self.args and self.args.config:
            service_json_path = self.args.config
        else:
            service_json_path = "service.json"

        with open(service_json_path) as f:
            service_json = json.load(f)

        agent_address = service_json.get('networks', {}).get(network_id, {}).get('agentAddress', None)
        need_agent = agent_address is None

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
            json.dump(metadata_json, tmp_json, ensure_ascii=False, sort_keys=True)
            tmp_json.seek(0)
            metadata_ipfs_hash = ipfs_client.add(tmp_json.name)["Hash"]
        metadata_ipfs_path = "/ipfs/{}".format(metadata_ipfs_hash)
        metadata_ipfs_uri = uri_reference(metadata_ipfs_path).copy_with(scheme='ipfs').unsplit()

        # Create or update Agent
        if need_agent:
            agent_factory_contract_def = get_contract_def("AgentFactory")
            agent_factory_address = self._getstring("agent_factory_at")
            cmd = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=agent_factory_address,
                    contract_function="createAgent",
                    contract_def=agent_factory_contract_def)(service_json["price"],
                                                             service_json['endpoint'], metadata_ipfs_uri),
                out_f=self.err_f,
                err_f=self.err_f,
                w3=self.w3,
                ident=self.ident)
            self._printerr("Creating transaction to create agent contract...\n")
            _, events = cmd.transact()

            # Update service.json with Agent address
            agent_address = events[0].args.agent
            if "networks" not in service_json:
                service_json['networks'] = {}
            service_json['networks'][network_id] = {"agentAddress": agent_address}
            self._printerr("Adding contract address to service.json file...\n")
            with open(service_json_path, "w+") as f:
                json.dump(service_json, f, indent=4, ensure_ascii=False)

        else:
            agent_contract_def = get_contract_def("Agent")

            agent_attributes = {
                "metadataURI": (metadata_ipfs_uri, "setMetadataURI", type_converter("string")),
                "currentPrice": (service_json["price"], "setPrice", type_converter("uint256")),
                "endpoint": (service_json["endpoint"], "setEndpoint", type_converter("string"))
            }

            for getter, (compare_to, setter, converter) in agent_attributes.items():
                current = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=agent_address,
                        contract_function=getter,
                        contract_def=agent_contract_def)(),
                    out_f=None,
                    err_f=None,
                    w3=self.w3,
                    ident=self.ident).call()
                if current != converter(compare_to):
                    cmd = ContractCommand(
                        config=self.config,
                        args=self.get_contract_argser(
                            contract_address=agent_address,
                            contract_function=setter,
                            contract_def=agent_contract_def)(converter(compare_to)),
                        out_f=self.err_f,
                        err_f=self.err_f,
                        w3=self.w3,
                        ident=self.ident)
                    self._printerr("Creating transaction to update agent contract's {} from {} to {}...\n".format(
                        getter, current, compare_to))
                    cmd.transact()

        organization = service_json.get("organization", "")
        if organization != "":
            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")

            (found, _, current_path, current_agent_address, current_tags) = self._getserviceregistrationbyname(service_json)

            if found:
                if (current_path != type_converter("bytes32")(service_json["path"]) or
                        current_agent_address != type_converter("address")(agent_address)):
                    cmd = ContractCommand(
                        config=self.config,
                        args=self.get_contract_argser(
                            contract_address=registry_address,
                            contract_function="updateServiceRegistration",
                            contract_def=registry_contract_def)(type_converter("bytes32")(organization),
                                                                type_converter("bytes32")(service_json["name"]),
                                                                type_converter("bytes32")(service_json["path"]),
                                                                type_converter("address")(agent_address)),
                        out_f=self.err_f,
                        err_f=self.err_f,
                        w3=self.w3,
                        ident=self.ident)
                    self._printerr("Creating transaction to update service registration...\n")
                    cmd.transact()

                current_tags_set = set(current_tags)
                new_tags_set = set([type_converter("bytes32")(tag) for tag in service_json["tags"]])

                if current_tags_set != new_tags_set:
                    remove_tags = current_tags_set - new_tags_set
                    add_tags = new_tags_set - current_tags_set

                    if len(remove_tags) > 0:
                        cmd = ContractCommand(
                            config=self.config,
                            args=self.get_contract_argser(
                                contract_address=registry_address,
                                contract_function="removeTagsFromServiceRegistration",
                                contract_def=registry_contract_def)(type_converter("bytes32")(organization),
                                                                    type_converter("bytes32")(service_json["name"]),
                                                                    [tag for tag in remove_tags]),
                            out_f=self.err_f,
                            err_f=self.err_f,
                            w3=self.w3,
                            ident=self.ident)
                        self._printerr("Creating transaction to remove tags {} from service registration...\n".format(
                            [tag.partition(b"\0")[0].decode("utf-8") for tag in remove_tags]))
                        cmd.transact()
                    if len(add_tags) > 0:
                        cmd = ContractCommand(
                            config=self.config,
                            args=self.get_contract_argser(
                                contract_address=registry_address,
                                contract_function="addTagsToServiceRegistration",
                                contract_def=registry_contract_def)(type_converter("bytes32")(organization),
                                                                    type_converter("bytes32")(service_json["name"]),
                                                                    [tag for tag in add_tags]),
                            out_f=self.err_f,
                            err_f=self.err_f,
                            w3=self.w3,
                            ident=self.ident)
                        self._printerr("Creating transaction to add tags {} to service registration...\n".format(
                            [tag.partition(b"\0")[0].decode("utf-8") for tag in add_tags]))
                        cmd.transact()
            else:
                # Register Agent
                if not self.args.no_register:
                    cmd = ContractCommand(
                        config=self.config,
                        args=self.get_contract_argser(
                            contract_address=registry_address,
                            contract_function="createServiceRegistration",
                            contract_def=registry_contract_def)(type_converter('bytes32')(service_json['organization']),
                                                                type_converter('bytes32')(service_json['name']),
                                                                type_converter('bytes32')(service_json['path']),
                                                                type_converter('address')(agent_address),
                                                                [type_converter('bytes32')(tag) for tag in service_json['tags']]),
                        out_f=self.err_f,
                        err_f=self.err_f,
                        w3=self.w3,
                        ident=self.ident)
                    self._printerr("Creating transaction to create service registration...\n")
                    cmd.transact()

    def update(self):
        network_id = self._get_network()

        if "config" in self.args and self.args.config:
            service_json_path = self.args.config
        else:
            service_json_path = "service.json"

        with open(service_json_path) as f:
            service_json = json.load(f)

        agent_contract_def = get_contract_def("Agent")

        if not service_json.get('networks', {}).get(network_id, {}).get('agentAddress', {}):
            self._error("Service hasn't been deployed to network with id {}".format(network_id))

        if self.args.new_price:
            current_price = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=service_json['networks'][network_id]['agentAddress'],
                    contract_function="price",
                    contract_def=agent_contract_def)(),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()
            if current_price != self.args.new_price:
                cmd = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=service_json['networks'][network_id]['agentAddress'],
                        contract_function="setPrice",
                        contract_def=agent_contract_def)(self.args.new_price),
                    out_f=self.err_f,
                    err_f=self.err_f,
                    w3=self.w3,
                    ident=self.ident)
                self._printerr("Creating transaction to update agent contract's price from {} to {}...\n".format(
                    current_price, self.args.new_price))
                cmd.transact()

        if self.args.new_endpoint:
            current_endpoint = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=service_json['networks'][network_id]['agentAddress'],
                    contract_function="endpoint",
                    contract_def=agent_contract_def)(),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()
            if current_endpoint != self.args.new_endpoint:
                cmd = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=service_json['networks'][network_id]['agentAddress'],
                        contract_function="setEndpoint",
                        contract_def=agent_contract_def)(self.args.new_endpoint),
                    out_f=self.err_f,
                    err_f=self.err_f,
                    w3=self.w3,
                    ident=self.ident)
                self._printerr("Creating transaction to update endpoint from {} to {}...\n".format(
                    current_endpoint, self.args.new_endpoint))
                cmd.transact()

        if self.args.new_description:
            # Get current metadata JSON
            current_metadata_uri = ContractCommand(
                config=self.config,
                args=self.get_contract_argser(
                    contract_address=service_json['networks'][network_id]['agentAddress'],
                    contract_function="metadataURI",
                    contract_def=agent_contract_def)(),
                out_f=None,
                err_f=None,
                w3=self.w3,
                ident=self.ident).call()
            ipfs_endpoint = urlparse(self.config["ipfs"]["default_ipfs_endpoint"])
            ipfs_scheme = ipfs_endpoint.scheme if ipfs_endpoint.scheme else "http"
            ipfs_port = ipfs_endpoint.port if ipfs_endpoint.port else 5001
            ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_endpoint.hostname), ipfs_port)
            ipfs_client.get(urlparse(current_metadata_uri).path)
            ipfs_file_path = Path.cwd().joinpath(urlparse(current_metadata_uri).path.split("/")[-1])
            with open(ipfs_file_path) as f:
                metadata_json = json.load(f)
            os.remove(ipfs_file_path)

            # Create new metadata JSON tmp file with updated description
            metadata_json['description'] = self.args.new_description
            with tempfile.NamedTemporaryFile(mode='w+') as tmp_json:
                json.dump(metadata_json, tmp_json, ensure_ascii=False, sort_keys=True)
                tmp_json.seek(0)
                metadata_ipfs_hash = ipfs_client.add(tmp_json.name)["Hash"]

            # Update metadataURI in the contract
            metadata_ipfs_path = "/ipfs/{}".format(metadata_ipfs_hash)
            metadata_ipfs_uri = uri_reference(metadata_ipfs_path).copy_with(scheme='ipfs').unsplit()

            if current_metadata_uri != metadata_ipfs_uri:
                cmd = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=service_json['networks'][network_id]["agentAddress"],
                        contract_function="setMetadataURI",
                        contract_def=agent_contract_def)(metadata_ipfs_uri),
                    out_f=self.err_f,
                    err_f=self.err_f,
                    w3=self.w3,
                    ident=self.ident)
                self._printerr("Creating transaction to update metadataURI from {} to {}...\n".format(
                    current_metadata_uri, metadata_ipfs_uri))
                cmd.transact()

        if self.args.new_tags:
            registry_contract_def = get_contract_def("Registry")
            registry_address = self._getstring("registry_at")

            (found, _, current_path, current_agent_address, current_tags) = self._getserviceregistrationbyname(service_json)

            if not found:
                self._error("Service hasn't been registered on network with id {}".format(network_id))

            current_tags_set = set(current_tags)
            new_tags_set = set(self.args.new_tags)

            if current_tags_set != new_tags_set:
                remove_tags = current_tags_set - new_tags_set
                add_tags = new_tags_set - current_tags_set

                if len(remove_tags) > 0:
                    cmd = ContractCommand(
                        config=self.config,
                        args=self.get_contract_argser(
                            contract_address=registry_address,
                            contract_function="removeTagsFromServiceRegistration",
                            contract_def=registry_contract_def)(type_converter("bytes32")(service_json['organization']),
                                                                type_converter("bytes32")(service_json["name"]),
                                                                [tag for tag in remove_tags]),
                        out_f=self.err_f,
                        err_f=self.err_f,
                        w3=self.w3,
                        ident=self.ident)
                    self._printerr("Creating transaction to remove tags {} from service registration...\n".format(
                        [tag.partition(b"\0")[0].decode("utf-8") for tag in remove_tags]))
                    cmd.transact()
                if len(add_tags) > 0:
                    cmd = ContractCommand(
                        config=self.config,
                        args=self.get_contract_argser(
                            contract_address=registry_address,
                            contract_function="addTagsToServiceRegistration",
                            contract_def=registry_contract_def)(type_converter("bytes32")(service_json['organization']),
                                                                type_converter("bytes32")(service_json["name"]),
                                                                [tag for tag in add_tags]),
                        out_f=self.err_f,
                        err_f=self.err_f,
                        w3=self.w3,
                        ident=self.ident)
                    self._printerr("Creating transaction to add tags {} to service registration...\n".format(
                        [tag.partition(b"\0")[0].decode("utf-8") for tag in add_tags]))
                    cmd.transact()

    def delete(self):

        if self.args.organization and self.args.name:
            self._printout("Getting information about the service...")
            network_id = self._get_network()

            (found, _, current_path, current_agent_address, current_tags) = self._getserviceregistrationbyname()

            if not found:
                self._error("Service {} is not registered on network with id {}".format(self.args.name, network_id))
            else:
                self._printerr("Deleting service {}...".format(self.args.name))
                registry_contract_def = get_contract_def("Registry")
                registry_address = self._getstring("registry_at")
                cmd = ContractCommand(
                    config=self.config,
                    args=self.get_contract_argser(
                        contract_address=registry_address,
                        contract_function="deleteServiceRegistration",
                        contract_def=registry_contract_def)(type_converter("bytes32")(self.args.organization),
                                                            type_converter("bytes32")(self.args.name)),
                    out_f=None,
                    err_f=None,
                    w3=self.w3,
                    ident=self.ident)
                try:
                    cmd.transact()
                except Exception as e:
                    self._printerr("\nTransaction error!\nHINT: Check your session and service json file.\n")
                    self._error(e)

            # Updating session
            self._printerr("Removing current contract address from session...\n")
            self._unset_key("current_agent_at", out_f=self.err_f)
            self._printout("Service was deleted!")