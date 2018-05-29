from setuptools import setup, find_packages

setup(
    name='snet-cli',
    version='0.1.3',
    packages=find_packages(),
    url='https://github.com/singnet/snet-cli',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET CLI',
    install_requires=[
        'jsonrpcclient==2.5.2',
        'web3==4.2.1',
        'mnemonic==0.18',
        'bip32utils==0.3.post3',
        'ecdsa==0.13',
        'trezor==0.9.1',
        'rlp==0.6.0',
        'PyYAML==3.12',
        'hidapi>=0.7.99',  # _vendor/ledgerblue
        'protobuf>=2.6.1',  # _vendor/ledgerblue
        'pycryptodome==3.6.1',  # _vendor/ledgerblue
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
