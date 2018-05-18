from setuptools import setup

setup(
    name='snet-cli',
    version='0.1.1',
    packages=['snet_cli'],
    scripts=['bin/snet'],
    url='https://github.com/singnet/snet-cli',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET CLI',
    install_requires=[
        'ledgerblue',
        'jsonrpcclient',
        'web3',
        'mnemonic',
        'bip32utils',
        'ecdsa',
        'trezor',
        'rlp==0.6.0',
        'PyYAML'
    ],
    include_package_data=True
)
