import json
import os
import subprocess
import functools
import sys

from urllib.parse import urlparse
from pathlib import Path, PurePath

import web3
import pkg_resources
import grpc
from grpc_tools.protoc import main as protoc


RESOURCES_PATH = PurePath(os.path.realpath(__file__)).parent.joinpath("resources")


class DefaultAttributeObject(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)

    def getstring(self, item):
        return getattr(self, item)

    def getint(self, item):
        if getattr(self, item) is None:
            return None
        return int(getattr(self, item))

    def getfloat(self, item):
        if getattr(self, item) is None:
            return None
        return float(getattr(self, item))

    def getboolean(self, item):
        if getattr(self, item) is None:
            return None
        i = self.getstring(item)
        if i in ["yes", "on", "true", "True", "1"]:
            return True
        return False

    def __getattr__(self, item):
        return self.__dict__.get(item, None)

    def __repr__(self):
        return self.__dict__.__repr__()

    def __str__(self):
        return self.__dict__.__str__()


def get_web3(rpc_endpoint):
    if rpc_endpoint.startswith("ws:"):
        provider = web3.WebsocketProvider(rpc_endpoint)
    else:
        provider = web3.HTTPProvider(rpc_endpoint)

    return web3.Web3(provider)


def serializable(o):
    if isinstance(o, bytes):
        return o.hex()
    else:
        return o.__dict__

def safe_address_converter(a):
    if not web3.eth.is_checksum_address(a):
        raise Exception("%s is not is not a valid Ethereum checksum address"%a)
    return a


def type_converter(t):
    if t.endswith("[]"):
        return lambda x: list(map(type_converter(t.replace("[]", "")), json.loads(x)))
    else:
        if "int" in t:
            return lambda x: web3.Web3.toInt(text=x)
        elif "bytes32" in t:
            return lambda x: web3.Web3.toBytes(text=x).ljust(32, b"\0") if not x.startswith("0x") else web3.Web3.toBytes(hexstr=x).ljust(32, b"\0")
        elif "byte" in t:
            return lambda x: web3.Web3.toBytes(text=x) if not x.startswith("0x") else web3.Web3.toBytes(hexstr=x)
        elif "address" in t:
            return safe_address_converter
        else:
            return str


def bytes32_to_str(b):
    return b.rstrip(b"\0").decode("utf-8")


def _add_next_paths(path, entry_path, seen_paths, next_paths):
    with open(path) as f:
        for line in f:
            if line.strip().startswith("import"):
                import_statement = "".join(line.split('"')[1::2])
                if not import_statement.startswith("google/protobuf"):
                    import_statement_path = Path(path.parent.joinpath(import_statement)).resolve()
                    if entry_path.parent in path.parents:
                        if import_statement_path not in seen_paths:
                            seen_paths.add(import_statement_path)
                            next_paths.append(import_statement_path)
                    else:
                        raise ValueError("Path must not be a parent of entry path")


def walk_imports(entry_path):
    seen_paths = set()
    next_paths = []
    for file_path in os.listdir(entry_path):
        if file_path.endswith(".proto"):
            file_path = entry_path.joinpath(file_path)
            seen_paths.add(file_path)
            next_paths.append(file_path)
    while next_paths:
        path = next_paths.pop()
        if os.path.isfile(path):
            _add_next_paths(path, entry_path, seen_paths, next_paths)
        else:
            raise IOError("Import path must be a valid file: {}".format(path))
    return seen_paths


def get_contract_def(contract_name, contract_artifacts_root=RESOURCES_PATH.joinpath("contracts")):
    contract_def = {}
    with open(Path(__file__).absolute().parent.joinpath(contract_artifacts_root, "abi", "{}.json".format(contract_name))) as f:
        contract_def["abi"] = json.load(f)
    if os.path.isfile(Path(__file__).absolute().parent.joinpath(contract_artifacts_root, "networks", "{}.json".format(contract_name))):
        with open(Path(__file__).absolute().parent.joinpath(contract_artifacts_root, "networks", "{}.json".format(contract_name))) as f:
            contract_def["networks"] = json.load(f)
    return contract_def


def read_temp_tar(f):
    f.flush()
    f.seek(0)
    return f


def get_cli_version():
    return pkg_resources.get_distribution("snet-cli").version


def compile_proto(entry_path, codegen_dir, proto_file=None, target_language="python"):
    try:
        if not os.path.exists(codegen_dir):
            os.makedirs(codegen_dir)
        proto_include = pkg_resources.resource_filename('grpc_tools', '_proto')

        compiler_args = [
            "-I{}".format(entry_path),
            "-I{}".format(proto_include)
        ]

        if target_language == "python":
            compiler_args.insert(0, "protoc")
            compiler_args.append("--python_out={}".format(codegen_dir))
            compiler_args.append("--grpc_python_out={}".format(codegen_dir)) 
            compiler = protoc
        elif target_language == "nodejs":
            protoc_node_compiler_path = Path(RESOURCES_PATH.joinpath("node_modules").joinpath("grpc-tools").joinpath("bin").joinpath("protoc.js")).absolute()
            grpc_node_plugin_path = Path(RESOURCES_PATH.joinpath("node_modules").joinpath("grpc-tools").joinpath("bin").joinpath("grpc_node_plugin")).resolve()
            if not os.path.isfile(protoc_node_compiler_path) or not os.path.isfile(grpc_node_plugin_path):
                print("Missing required node.js protoc compiler. Retrieving from npm...")
                subprocess.run(["npm", "install"], cwd=RESOURCES_PATH)
            compiler_args.append("--js_out=import_style=commonjs,binary:{}".format(codegen_dir))
            compiler_args.append("--grpc_out={}".format(codegen_dir))
            compiler_args.append("--plugin=protoc-gen-grpc={}".format(grpc_node_plugin_path))
            compiler = lambda args: subprocess.run([str(protoc_node_compiler_path)] + args)

        if proto_file:
            compiler_args.append(str(proto_file))
        else:
            compiler_args.extend([str(p) for p in entry_path.glob("**/*.proto")])

        if not compiler(compiler_args):
            return True
        else:
            return False

    except Exception as e:
        print(e)
        return False

def abi_get_element_by_name(abi, name):
    """ Return element of abi (return None if fails to find) """
    if (abi and "abi" in abi):
        for a in abi["abi"]:
            if ("name" in a and a["name"] == name):
                return a
    return None

def abi_decode_struct_to_dict(abi, struct_list):
    return {el_abi["name"] : el for el_abi, el in zip(abi["outputs"], struct_list)}


def int4bytes_big(b):
    return int.from_bytes(b, byteorder='big')


def is_valid_endpoint(url):
    """
    Just ensures the url has a scheme (http/https), and a net location (IP or domain name).
    Can make more advanced or do on-network tests if needed, but this is really just to catch obvious errors.
    >>> is_valid_endpoint("https://34.216.72.29:6206")
    True
    >>> is_valid_endpoint("blahblah")
    False
    >>> is_valid_endpoint("blah://34.216.72.29")
    False
    >>> is_valid_endpoint("http://34.216.72.29:%%%")
    False
    >>> is_valid_endpoint("http://192.168.0.2:9999")
    True
    """
    try:
        result = urlparse(url)
        if result.port:
            _port = int(result.port)
        return (
            all([result.scheme, result.netloc]) and
            result.scheme in ['http', 'https']
        )
    except ValueError:
        return False


def remove_http_https_prefix(endpoint):
    """remove http:// or https:// prefix if presented in endpoint"""
    endpoint = endpoint.replace("https://","")
    endpoint = endpoint.replace("http://","")
    return endpoint

def open_grpc_channel(endpoint):
    """
       open grpc channel:
           - for http://  we open insecure_channel
           - for https:// we open secure_channel (with default credentials)
           - without prefix we open insecure_channel
    """
    if (endpoint.startswith("https://")):
        return grpc.secure_channel(remove_http_https_prefix(endpoint), grpc.ssl_channel_credentials())
    return grpc.insecure_channel(remove_http_https_prefix(endpoint))

def rgetattr(obj, attr):
    """
    >>> from types import SimpleNamespace
    >>> args = SimpleNamespace(a=1, b=SimpleNamespace(c=2, d='e'))
    >>> rgetattr(args, "a")
    1
    >>> rgetattr(args, "b.c")
    2
    """
    return functools.reduce(getattr, [obj] + attr.split('.'))


def get_contract_object(w3, contract_file):
    with open(RESOURCES_PATH.joinpath("contracts", "abi", contract_file)) as f:
        abi = json.load(f)
    with open(RESOURCES_PATH.joinpath("contracts", "networks", contract_file)) as f:
        networks = json.load(f)
        address = w3.toChecksumAddress(networks[w3.version.network]["address"])
    return w3.eth.contract(abi=abi, address=address)


def get_contract_deployment_block(w3, contract_file):
    with open(RESOURCES_PATH.joinpath("contracts", "networks", contract_file)) as f:
        networks = json.load(f)
        txn_hash = networks[w3.version.network]["transactionHash"]
    return w3.eth.getTransactionReceipt(txn_hash).blockNumber


def normalize_private_key(private_key):
    if private_key.startswith("0x"):
        private_key = bytes(bytearray.fromhex(private_key[2:]))
    else:
        private_key = bytes(bytearray.fromhex(private_key))
    return private_key


def get_address_from_private(private_key):
    return web3.eth.Account.privateKeyToAccount(private_key).address


class add_to_path():
    def __init__(self, path):
        self.path = path
    def __enter__(self):
        sys.path.insert(0, self.path)
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            sys.path.remove(self.path)
        except ValueError:
            pass
