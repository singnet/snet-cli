from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install


common_dependencies = [
    'protobuf==4.21.6',
    'grpcio-tools==1.59.0',
    'wheel==0.41.2',
    'jsonrpcclient==4.0.3',
    'eth-hash==0.5.2',
    'rlp==3.0.0',
    'eth-rlp==0.3.0',
    'web3==6.11.1',
    'mnemonic==0.20',
    'pycoin==0.92.20230326',
    'pyyaml==6.0.1',
    'ipfshttpclient==0.4.13.2',
    'rfc3986==2.0.0',
    'pymultihash==0.8.2',
    'base58==2.1.1',
    'argcomplete==3.1.2',
    'grpcio-health-checking==1.59.0',
    'jsonschema==4.0.0',
    'eth-account==0.9.0',
]


def install_and_compile_proto():
    import snet.snet_cli
    from snet.snet_cli.utils.utils import compile_proto as compile_proto
    from pathlib import Path
    proto_dir = Path(__file__).absolute().parent.joinpath(
        "snet", "snet_cli", "resources", "proto")
    dest_dir = Path(snet.snet_cli.__file__).absolute(
    ).parent.joinpath("resources", "proto")
    print(proto_dir, "->", dest_dir)
    for fn in proto_dir.glob('*.proto'):
        print("Compiling protobuf", fn)
        compile_proto(proto_dir, dest_dir, proto_file=fn)


class develop(_develop):
    """Post-installation for development mode."""

    def run(self):
        _develop.run(self)
        self.execute(install_and_compile_proto, (),
                     msg="Compile protocol buffers")


class install(_install):
    """Post-installation for installation mode."""

    def run(self):
        _install.run(self)
        self.execute(install_and_compile_proto, (),
                     msg="Compile protocol buffers")
