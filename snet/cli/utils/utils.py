import json
import os
import subprocess
import functools
import re
import sys
import importlib.resources
from importlib.metadata import distribution
from urllib.parse import urlparse
from pathlib import Path, PurePath
from lighthouseweb3 import Lighthouse
import io
import tarfile

import web3
import grpc
from grpc_tools.protoc import main as protoc
from trezorlib.cli.firmware import download

from snet import cli
from snet.cli.resources.root_certificate import certificate
from snet.cli.utils.ipfs_utils import get_from_ipfs_and_checkhash

RESOURCES_PATH = PurePath(os.path.dirname(cli.__file__)).joinpath("resources")


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
    if not web3.Web3.is_checksum_address(a):
        raise Exception("%s is not is not a valid Ethereum checksum address" % a)
    return a


def type_converter(t):
    if t.endswith("[]"):
        return lambda x: list(map(type_converter(t.replace("[]", "")), json.loads(x)))
    else:
        if "int" in t:
            return lambda x: web3.Web3.to_int(text=x)
        elif "bytes32" in t:
            return lambda x: web3.Web3.to_bytes(text=x).ljust(32, b"\0") if not x.startswith(
                "0x") else web3.Web3.to_bytes(hexstr=x).ljust(32, b"\0")
        elif "byte" in t:
            return lambda x: web3.Web3.to_bytes(text=x) if not x.startswith("0x") else web3.Web3.to_bytes(hexstr=x)
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


def read_temp_tar(f):
    f.flush()
    f.seek(0)
    return f


def get_cli_version():
    return distribution("snet.cli").version


def compile_proto(entry_path, codegen_dir, proto_file=None, add_training=False):
    try:
        if not os.path.exists(codegen_dir):
            os.makedirs(codegen_dir)
        proto_include = importlib.resources.files('grpc_tools') / '_proto'

        compiler_args = [
            "-I{}".format(entry_path),
            "-I{}".format(proto_include)
        ]

        if add_training:
            training_include = RESOURCES_PATH.joinpath("proto", "training")
            compiler_args.append("-I{}".format(training_include))

        compiler_args.insert(0, "protoc")
        compiler_args.append("--python_out={}".format(codegen_dir))
        compiler_args.append("--grpc_python_out={}".format(codegen_dir))
        compiler = protoc

        if proto_file:
            compiler_args.append(str(proto_file))
        else:
            compiler_args.extend([str(p) for p in entry_path.glob("**/*.proto")])

        if add_training:
            compiler_args.append(str(training_include.joinpath("training.proto")))

        if not compiler(compiler_args):
            return True
        else:
            return False

    except Exception as e:
        print(e)
        return False


def abi_get_element_by_name(abi, name):
    """ Return element of abi (return None if fails to find) """
    if abi and "abi" in abi:
        for a in abi["abi"]:
            if "name" in a and a["name"] == name:
                return a
    return None


def abi_decode_struct_to_dict(abi, struct_list):
    return {el_abi["name"]: el for el_abi, el in zip(abi["outputs"], struct_list)}


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
    endpoint = endpoint.replace("https://", "")
    endpoint = endpoint.replace("http://", "")
    return endpoint


def open_grpc_channel(endpoint):
    """
       open grpc channel:
           - for http://  we open insecure_channel
           - for https:// we open secure_channel (with default credentials)
           - without prefix we open insecure_channel
    """
    _GB = 1024 ** 3
    options = [('grpc.max_send_message_length', _GB),
               ('grpc.max_receive_message_length', _GB)]
    if endpoint.startswith("https://"):
        return grpc.secure_channel(remove_http_https_prefix(endpoint), grpc.ssl_channel_credentials(root_certificates=certificate))
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


def normalize_private_key(private_key):
    if private_key.startswith("0x"):
        private_key = bytes(bytearray.fromhex(private_key[2:]))
    else:
        private_key = bytes(bytearray.fromhex(private_key))
    return private_key


def get_address_from_private(private_key):
    return web3.Account.from_key(private_key).address


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


def find_file_by_keyword(directory, keyword):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if keyword in file:
                    return file


def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None


def bytesuri_to_hash(s, to_decode=True):
    if to_decode:
        s = s.rstrip(b"\0").decode('ascii')
    if s.startswith("ipfs://"):
        return "ipfs", s[7:]
    elif s.startswith("filecoin://"):
        return "filecoin", s[11:]
    else:
        raise Exception("We support only ipfs and filecoin uri in Registry")


def get_file_from_filecoin(cid):
    lighthouse_client = Lighthouse(" ")
    downloaded_file, _ = lighthouse_client.download(cid)
    return downloaded_file


def download_and_safe_extract_proto(service_api_source, protodir, ipfs_client):
    """
    Tar files might be dangerous (see https://bugs.python.org/issue21109,
    and https://docs.python.org/3/library/tarfile.html, TarFile.extractall warning)
    we extract only simple files
    """
    try:
        storage_type, service_api_source = bytesuri_to_hash(service_api_source, to_decode=False)
    except Exception:
        storage_type = "ipfs"

    if storage_type == "ipfs":
        spec_tar = get_from_ipfs_and_checkhash(ipfs_client, service_api_source)
    else:
        spec_tar = get_file_from_filecoin(service_api_source)

    with tarfile.open(fileobj=io.BytesIO(spec_tar)) as f:
        for m in f.getmembers():
            if os.path.dirname(m.name) != "":
                raise Exception(
                    "tarball has directories. We do not support it.")
            if not m.isfile():
                raise Exception(
                    "tarball contains %s which is not a files" % m.name)
            fullname = os.path.join(protodir, m.name)
            if os.path.exists(fullname):
                os.remove(fullname)
                print("%s removed." % fullname)
        # now it is safe to call extractall
        f.extractall(protodir)


def check_training_in_proto(protodir) -> bool:
    files = os.listdir(protodir)
    for file in files:
        if ".proto" not in file:
            continue
        with open(protodir.joinpath(file), "r") as f:
            proto_text = f.read()
        if 'import "training.proto";' in proto_text:
            return True
    return False