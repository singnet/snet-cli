from setuptools import setup

setup(
    name='snet-cli',
    version='0.1.2',
    packages=['snet_cli'],
    scripts=['bin/snet'],
    url='https://github.com/singnet/snet-cli',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET CLI',
    install_requires=[
        'jsonrpcclient',
        'web3',
        'mnemonic',
        'bip32utils',
        'ecdsa',
        'trezor',
        'rlp==0.6.0',
        'PyYAML',
        'hidapi>=0.7.99',  # _vendor/ledgerblue
        'protobuf>=2.6.1',  # _vendor/ledgerblue
        'pycryptodome',  # _vendor/ledgerblue
        'future',  # _vendor/ledgerblue
        'ecpy>=0.8.1',  # _vendor/ledgerblue
        'pillow>=3.4.0',  # _vendor/ledgerblue
        'python-u2flib-host>=3.0.2'  # _vendor/ledgerblue
    ],
    include_package_data=True
)
