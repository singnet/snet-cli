import os 
import json
from pathlib import PurePath

import web3
import ecdsa
import hashlib


cur_dir = PurePath(os.path.realpath(__file__)).parent


def get_contract_object(w3, contract_file):
    with open(cur_dir.joinpath("resources", "contracts", "abi", contract_file)) as f:
        abi = json.load(f)
    with open(cur_dir.joinpath("resources", "contracts", "networks", contract_file)) as f:
        networks = json.load(f)
        address = w3.toChecksumAddress(networks[w3.version.network]["address"])
    return w3.eth.contract(abi=abi, address=address)


def get_contract_deployment_block(w3, contract_file):
    with open(cur_dir.joinpath("resources", "contracts", "networks", contract_file)) as f:
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
    public_key = ecdsa.SigningKey.from_string(string=private_key,
                                              curve=ecdsa.SECP256k1,
                                              hashfunc=hashlib.sha256).get_verifying_key()
    return web3.Web3.toChecksumAddress("0x" + web3.Web3.sha3(hexstr=public_key.to_string().hex())[12:].hex())
