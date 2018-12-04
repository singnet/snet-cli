import abc
import hashlib
import struct
import time

from pycoin.key.BIP32Node import BIP32Node
import ecdsa
import rlp
from eth_account.internal.transactions import serializable_unsigned_transaction_from_dict, encode_transaction, \
    UnsignedTransaction
from eth_account.messages import defunct_hash_message
from mnemonic import Mnemonic
from trezorlib.client import TrezorClient, proto
from trezorlib.transport_hid import HidTransport

from snet_cli._vendor.ledgerblue.comm import getDongle
from snet_cli._vendor.ledgerblue.commException import CommException

BIP32_HARDEN = 0x80000000


class IdentityProvider(abc.ABC):
    @abc.abstractmethod
    def get_address(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def transact(self, transaction, out_f):
        raise NotImplementedError()

    @abc.abstractmethod
    def sign_message_after_soliditySha3(self, message):
        raise NotImplementedError()


class KeyIdentityProvider(IdentityProvider):
    def __init__(self, w3, private_key):
        self.w3 = w3
        if private_key.startswith("0x"):
            self.private_key = bytes(bytearray.fromhex(private_key[2:]))
        else:
            self.private_key = bytes(bytearray.fromhex(private_key))

        public_key = ecdsa.SigningKey.from_string(string=self.private_key,
                                                  curve=ecdsa.SECP256k1,
                                                  hashfunc=hashlib.sha256).get_verifying_key()

        self.address = self.w3.toChecksumAddress("0x" + self.w3.sha3(hexstr=public_key.to_string().hex())[12:].hex())

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        raw_transaction = self.w3.eth.account.signTransaction(transaction, self.private_key).rawTransaction
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)
    
    def sign_message_after_soliditySha3(self, message):
        h = defunct_hash_message(message)
        return self.w3.eth.account.signHash(h, self.private_key).signature

class RpcIdentityProvider(IdentityProvider):
    def __init__(self, w3, index):
        self.w3 = w3
        self.address = self.w3.personal.listAccounts[index]

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        print("Submitting transaction...\n", file=out_f)
        txn_hash = self.w3.eth.sendTransaction(transaction)
        return send_and_wait_for_transaction_receipt(txn_hash, self.w3)

    def sign_message_after_soliditySha3(self, message):
        return self.w3.eth.sign(self.get_address(), message)

class MnemonicIdentityProvider(IdentityProvider):
    def __init__(self, w3, mnemonic, index):
        self.w3 = w3
        master_key = BIP32Node.from_master_secret(Mnemonic("english").to_seed(mnemonic))
        purpose_subtree = master_key.subkey(i=44, is_hardened=True)
        coin_type_subtree = purpose_subtree.subkey(i=60, is_hardened=True)
        account_subtree = coin_type_subtree.subkey(i=0, is_hardened=True)
        change_subtree = account_subtree.subkey(i=0)
        account = change_subtree.subkey(i=index)
        self.private_key = account.secret_exponent().to_bytes(32, 'big')

        public_key = ecdsa.SigningKey.from_string(string=self.private_key,
                                                  curve=ecdsa.SECP256k1,
                                                  hashfunc=hashlib.sha256).get_verifying_key()

        self.address = self.w3.toChecksumAddress(
            "0x" + self.w3.sha3(hexstr=public_key.to_string().hex())[12:].hex())

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        raw_transaction = self.w3.eth.account.signTransaction(transaction, self.private_key).rawTransaction
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_soliditySha3(self, message):
        h = defunct_hash_message(message)
        return self.w3.eth.account.signHash(h, self.private_key).signature


class TrezorIdentityProvider(IdentityProvider):
    def __init__(self, w3, index):
        self.w3 = w3
        self.client = TrezorClient(HidTransport.enumerate()[0])
        self.index = index
        self.address = self.w3.toChecksumAddress(
            "0x" + bytes(self.client.ethereum_get_address([44 + BIP32_HARDEN,
                                                           60 + BIP32_HARDEN,
                                                           BIP32_HARDEN, 0,
                                                           index])).hex())

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        print("Sending transaction to trezor for signature...\n", file=out_f)
        signature = self.client.ethereum_sign_tx(n=[44 + BIP32_HARDEN, 60 + BIP32_HARDEN,
                                                    BIP32_HARDEN, 0, self.index],
                                                 nonce=transaction["nonce"],
                                                 gas_price=transaction["gasPrice"],
                                                 gas_limit=transaction["gas"],
                                                 to=bytearray.fromhex(transaction["to"][2:]),
                                                 value=transaction["value"],
                                                 data=bytearray.fromhex(transaction["data"][2:]))

        transaction.pop("from")
        unsigned_transaction = serializable_unsigned_transaction_from_dict(transaction)
        raw_transaction = encode_transaction(unsigned_transaction,
                                             vrs=(signature[0],
                                                  int(signature[1].hex(), 16),
                                                  int(signature[2].hex(), 16)))
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_soliditySha3(self, message):
        n = self.client._convert_prime([44 + BIP32_HARDEN,
                                        60 + BIP32_HARDEN,
                                        BIP32_HARDEN,
                                        0,
                                        self.index])
        return self.client.call(proto.EthereumSignMessage(address_n=n, message=message)).signature

def send_and_wait_for_transaction_receipt(txn_hash, w3):
    # Wait for transaction to be mined
    receipt = dict()
    while not receipt:
        time.sleep(1)
        receipt = w3.eth.getTransactionReceipt(txn_hash)
        if receipt and "blockHash" in receipt and receipt["blockHash"] is None:
            receipt = dict()
    return receipt


def send_and_wait_for_transaction(raw_transaction, w3, out_f):
    print("Submitting transaction...\n", file=out_f)
    txn_hash = w3.eth.sendRawTransaction(raw_transaction)
    return send_and_wait_for_transaction_receipt(txn_hash, w3)


def parse_bip32_path(path):
    if len(path) == 0:
        return b""
    result = b""
    elements = path.split('/')
    for pathElement in elements:
        element = pathElement.split('\'')
        if len(element) == 1:
            result = result + struct.pack(">I", int(element[0]))
        else:
            result = result + struct.pack(">I", BIP32_HARDEN | int(element[0]))
    return result


class LedgerIdentityProvider(IdentityProvider):
    GET_ADDRESS_OP = b"\xe0\x02\x00\x00"
    SIGN_TX_OP = b"\xe0\x04\x00\x00"
    SIGN_TX_OP_CONT = b"\xe0\x04\x80\x00"
    SIGN_MESSAGE_OP = b"\xe0\x08\x00\x00"

    def __init__(self, w3, index):
        self.w3 = w3
        try:
            self.dongle = getDongle(False)
        except CommException:
            raise RuntimeError("Received commException from ledger. Are you sure your device is plugged in?")
        self.dongle_path = parse_bip32_path("44'/60'/0'/0/{}".format(index))
        apdu = LedgerIdentityProvider.GET_ADDRESS_OP
        apdu += bytearray([len(self.dongle_path) + 1, int(len(self.dongle_path) / 4)]) + self.dongle_path
        try:
            result = self.dongle.exchange(apdu)
        except CommException:
            raise RuntimeError("Received commException from ledger. Are you sure your device is unlocked and the "
                               "Ethereum app is running?")

        offset = 1 + result[0]
        self.address = self.w3.toChecksumAddress(bytes(result[offset + 1: offset + 1 + result[offset]])
                                                 .decode("utf-8"))

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        tx = UnsignedTransaction(
            nonce=transaction["nonce"],
            gasPrice=transaction["gasPrice"],
            gas=transaction["gas"],
            to=bytes(bytearray.fromhex(transaction["to"][2:])),
            value=transaction["value"],
            data=bytes(bytearray.fromhex(transaction["data"][2:]))
        )

        encoded_tx = rlp.encode(tx, UnsignedTransaction)

        overflow = len(self.dongle_path) + 1 + len(encoded_tx) - 255

        if overflow > 0:
            encoded_tx, remaining_tx = encoded_tx[:-overflow], encoded_tx[-overflow:]

        apdu = LedgerIdentityProvider.SIGN_TX_OP
        apdu += bytearray([len(self.dongle_path) + 1 + len(encoded_tx), int(len(self.dongle_path) / 4)])
        apdu += self.dongle_path + encoded_tx
        try:
            print("Sending transaction to ledger for signature...\n", file=out_f)
            result = self.dongle.exchange(apdu)
            while overflow > 0:
                encoded_tx = remaining_tx
                overflow = len(encoded_tx) - 255

                if overflow > 0:
                    encoded_tx, remaining_tx = encoded_tx[:-overflow], encoded_tx[-overflow:]

                apdu = LedgerIdentityProvider.SIGN_TX_OP_CONT
                apdu += bytearray([len(encoded_tx)])
                apdu += encoded_tx
                result = self.dongle.exchange(apdu)
        except CommException:
            raise RuntimeError("Received commException from ledger. Are you sure your device is unlocked and the "
                               "Ethereum app is running?")

        transaction.pop("from")
        unsigned_transaction = serializable_unsigned_transaction_from_dict(transaction)
        raw_transaction = encode_transaction(unsigned_transaction,
                                             vrs=(result[0],
                                                  int.from_bytes(result[1:33], byteorder="big"),
                                                  int.from_bytes(result[33:65], byteorder="big")))
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_soliditySha3(self, message):
        apdu = LedgerIdentityProvider.SIGN_MESSAGE_OP
        apdu += bytearray([len(self.dongle_path) + 1 + len(message) + 4, int(len(self.dongle_path) / 4)])
        apdu += self.dongle_path + struct.pack(">I", len(message)) + message
        try:
            result = self.dongle.exchange(apdu)
        except CommException:
            raise RuntimeError("Received commException from ledger. Are you sure your device is unlocked and the "
                               "Ethereum app is running?")

        return result[1:] + result[0:1]


def get_kws_for_identity_type(identity_type):
    SECRET = True
    PLAINTEXT = False

    if identity_type == "rpc":
        return [("network", PLAINTEXT)]
    elif identity_type == "mnemonic":
        return [("mnemonic", SECRET)]
    elif identity_type == "key":
        return [("private_key", SECRET)]
    elif identity_type == "trezor":
        return []
    elif identity_type == "ledger":
        return []
    else:
        raise RuntimeError("unrecognized identity_type {}".format(identity_type))


def get_identity_types():
    return ["rpc", "mnemonic", "key", "trezor", "ledger"]
