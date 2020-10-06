import abc
import json
import struct
import time
import getpass

import web3
from pycoin.key.BIP32Node import BIP32Node
import rlp
from eth_account.internal.transactions import serializable_unsigned_transaction_from_dict, encode_transaction, \
    UnsignedTransaction
from eth_account.messages import defunct_hash_message
from mnemonic import Mnemonic
from trezorlib.client import TrezorClient, proto
from trezorlib.transport_hid import HidTransport

from ledgerblue.comm import getDongle
from ledgerblue.commException import CommException

from snet.snet_cli.utils.utils import get_address_from_private, normalize_private_key


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
        self.private_key = normalize_private_key(private_key)
        self.address = get_address_from_private(self.private_key)

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        raw_transaction = sign_transaction_with_private_key(
            self.w3, self.private_key, transaction)
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_soliditySha3(self, message):
        return sign_message_with_private_key(self.w3, self.private_key, message)


class KeyStoreIdentityProvider(IdentityProvider):
    def __init__(self, w3, path_to_keystore):
        self.w3 = w3
        try:
            with open(path_to_keystore) as keyfile:
                encrypted_key = keyfile.read()
                self.address = self.w3.toChecksumAddress(
                    json.loads(encrypted_key)["address"])
                self.path_to_keystore = path_to_keystore
                self.private_key = None
        except CommException:
            raise RuntimeError(
                "Error decrypting your keystore. Are you sure it is the correct path?")

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):

        if self.private_key is None:
            self.private_key = unlock_keystore_with_password(
                self.w3, self.path_to_keystore)

        raw_transaction = sign_transaction_with_private_key(
            self.w3, self.private_key, transaction)
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_soliditySha3(self, message):

        if self.private_key is None:
            self.private_key = unlock_keystore_with_password(
                self.w3, self.path_to_keystore)

        return sign_message_with_private_key(self.w3, self.private_key, message)


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
        master_key = BIP32Node.from_master_secret(
            Mnemonic("english").to_seed(mnemonic))
        purpose_subtree = master_key.subkey(i=44, is_hardened=True)
        coin_type_subtree = purpose_subtree.subkey(i=60, is_hardened=True)
        account_subtree = coin_type_subtree.subkey(i=0, is_hardened=True)
        change_subtree = account_subtree.subkey(i=0)
        account = change_subtree.subkey(i=index)
        self.private_key = account.secret_exponent().to_bytes(32, 'big')
        self.address = get_address_from_private(self.private_key)

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        raw_transaction = sign_transaction_with_private_key(
            self.w3, self.private_key, transaction)
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_soliditySha3(self, message):
        return sign_message_with_private_key(self.w3, self.private_key, message)


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
                                                 to=bytearray.fromhex(
                                                     transaction["to"][2:]),
                                                 value=transaction["value"],
                                                 data=bytearray.fromhex(transaction["data"][2:]))

        transaction.pop("from")
        unsigned_transaction = serializable_unsigned_transaction_from_dict(
            transaction)
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
            raise RuntimeError(
                "Received commException from ledger. Are you sure your device is plugged in?")
        self.dongle_path = parse_bip32_path("44'/60'/0'/0/{}".format(index))
        apdu = LedgerIdentityProvider.GET_ADDRESS_OP
        apdu += bytearray([len(self.dongle_path) + 1,
                           int(len(self.dongle_path) / 4)]) + self.dongle_path
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
            encoded_tx, remaining_tx = encoded_tx[:-
                                                  overflow], encoded_tx[-overflow:]

        apdu = LedgerIdentityProvider.SIGN_TX_OP
        apdu += bytearray([len(self.dongle_path) + 1 +
                           len(encoded_tx), int(len(self.dongle_path) / 4)])
        apdu += self.dongle_path + encoded_tx
        try:
            print("Sending transaction to ledger for signature...\n", file=out_f)
            result = self.dongle.exchange(apdu)
            while overflow > 0:
                encoded_tx = remaining_tx
                overflow = len(encoded_tx) - 255

                if overflow > 0:
                    encoded_tx, remaining_tx = encoded_tx[:-
                                                          overflow], encoded_tx[-overflow:]

                apdu = LedgerIdentityProvider.SIGN_TX_OP_CONT
                apdu += bytearray([len(encoded_tx)])
                apdu += encoded_tx
                result = self.dongle.exchange(apdu)
        except CommException:
            raise RuntimeError("Received commException from ledger. Are you sure your device is unlocked and the "
                               "Ethereum app is running?")

        transaction.pop("from")
        unsigned_transaction = serializable_unsigned_transaction_from_dict(
            transaction)
        raw_transaction = encode_transaction(unsigned_transaction,
                                             vrs=(result[0],
                                                  int.from_bytes(
                                                      result[1:33], byteorder="big"),
                                                  int.from_bytes(result[33:65], byteorder="big")))
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_soliditySha3(self, message):
        apdu = LedgerIdentityProvider.SIGN_MESSAGE_OP
        apdu += bytearray([len(self.dongle_path) + 1 +
                           len(message) + 4, int(len(self.dongle_path) / 4)])
        apdu += self.dongle_path + struct.pack(">I", len(message)) + message
        try:
            result = self.dongle.exchange(apdu)
        except CommException:
            raise RuntimeError("Received commException from ledger. Are you sure your device is unlocked and the "
                               "Ethereum app is running?")

        return result[1:] + result[0:1]


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
    elif identity_type == "keystore":
        return [("keystore_path", PLAINTEXT)]
    else:
        raise RuntimeError(
            "unrecognized identity_type {}".format(identity_type))


def get_identity_types():
    return ["rpc", "mnemonic", "key", "trezor", "ledger", "keystore"]


def sign_transaction_with_private_key(w3, private_key, transaction):
    return w3.eth.account.signTransaction(transaction, private_key).rawTransaction


def sign_message_with_private_key(w3, private_key, message):
    h = defunct_hash_message(message)
    return w3.eth.account.signHash(h, private_key).signature


def unlock_keystore_with_password(w3, path_to_keystore):
    password = getpass.getpass("Password : ") or ""
    with open(path_to_keystore) as keyfile:
        encrypted_key = keyfile.read()
        return w3.eth.account.decrypt(encrypted_key, password)
