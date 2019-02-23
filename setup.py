from setuptools import setup, find_packages
from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install
import re


def install_and_compile_proto():
    import snet_cli
    from snet_cli.utils import compile_proto as compile_proto
    from pathlib import Path
    proto_dir = Path(__file__).absolute().parent.joinpath("snet_cli", "resources", "proto")
    dest_dir = Path(snet_cli.__file__).absolute().parent.joinpath("resources", "proto")
    print(proto_dir, "->", dest_dir)
    for fn in proto_dir.glob('*.proto'):
        print("Compiling protobuf", fn)
        compile_proto(proto_dir, dest_dir, proto_file=fn)

class develop(_develop):
    """Post-installation for development mode."""
    def run(self):
        _develop.run(self)
        self.execute(install_and_compile_proto, (), msg="Compile protocol buffers")

class install(_install):
    """Post-installation for installation mode."""
    def run(self):
        _install.run(self)
        self.execute(install_and_compile_proto, (), msg="Compile protocol buffers")


with open('snet_cli/__init__.py', 'rt', encoding='utf8') as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
    name='snet-cli',
    version=version,
    packages=find_packages(),
    url='https://github.com/singnet/snet-cli',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET CLI',
    python_requires='>=3.6',
    install_requires=[
        'grpcio-tools==1.17.1',
        'jsonrpcclient==2.5.2',
        'web3==4.2.1',
        'mnemonic==0.18',
        'pycoin>=0.80',
        'ecdsa==0.13',
        'trezor==0.9.1',
        'rlp==1.0.1',
        'pyyaml>=4.2b1',
        'ipfsapi==0.4.2.post1',
        'rfc3986==1.1.0',
        'hidapi>=0.7.99',  # _vendor/ledgerblue
        'protobuf>=2.6.1',  # _vendor/ledgerblue
        'pycryptodome>=3.6.6',  # _vendor/ledgerblue
        'eth-hash==0.1.4',  # the latest eth-hash v0.2.0 requires pycryptodome>=3.6.6,<4
        'future==0.16.0',  # _vendor/ledgerblue
        'ecpy>=0.8.1',  # _vendor/ledgerblue
        'pillow>=3.4.0',  # _vendor/ledgerblue
        'python-u2flib-host>=3.0.2',  # _vendor/ledgerblue
        'pymultihash==0.8.2',
        'base58==1.0.2'
    ],
    cmdclass={
        'develop': develop,
        'install': install,
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'snet = snet_cli:main',
        ],
    }
)
