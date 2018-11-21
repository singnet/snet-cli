from setuptools import setup, find_packages
import re

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
    install_requires=[
        'grpcio-tools==1.14.1',
        'jsonrpcclient==2.5.2',
        'eth-typing<2', # workaround until next version after eth-abi v2.0.0-beta.1 is released
        'web3==4.2.1',
        'mnemonic==0.18',
        'pycoin>=0.80',
        'ecdsa==0.13',
        'trezor==0.9.1',
        'rlp==0.6.0',
        'PyYAML==3.12',
        'ipfsapi==0.4.2.post1',
        'rfc3986==1.1.0',
        'hidapi>=0.7.99',  # _vendor/ledgerblue
        'protobuf>=2.6.1',  # _vendor/ledgerblue
        'pycryptodome>=3.6.6',  # _vendor/ledgerblue
        'eth-hash==0.1.4',  # the latest eth-hash v0.2.0 requires pycryptodome>=3.6.6,<4
        'future==0.16.0',  # _vendor/ledgerblue
        'ecpy>=0.8.1',  # _vendor/ledgerblue
        'pillow>=3.4.0',  # _vendor/ledgerblue
        'python-u2flib-host>=3.0.2'  # _vendor/ledgerblue
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'snet = snet_cli:main',
        ],
    }
)
