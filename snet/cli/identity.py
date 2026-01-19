import abc
import json
import struct
import time
import getpass

import rlp
from eth_account import Account
from eth_account.messages import encode_defunct
from ledgerblue.comm import getDongle
from ledgerblue.commException import CommException
from rlp.sedes import big_endian_int, binary
from trezorlib.client import TrezorClient
from trezorlib.transport import get_transport
from trezorlib import ethereum, tools, ui


from snet.cli.utils.utils import get_address_from_private, normalize_private_key

BIP32_HARDEN = 0x80000000


class IdentityProvider(abc.ABC):
    @abc.abstractmethod
    def get_address(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def transact(self, transaction, out_f):
        raise NotImplementedError()

    @abc.abstractmethod
    def sign_message_after_solidity_keccak(self, message):
        raise NotImplementedError()


class Transaction(rlp.Serializable):
    fields = [
        ('nonce', big_endian_int),
        ('gasPrice', big_endian_int),
        ('gas', big_endian_int),
        ('to', binary),
        ('value', big_endian_int),
        ('data', binary),
        ('v', big_endian_int),
        ('r', big_endian_int),
        ('s', big_endian_int),
    ]


class KeyIdentityProvider(IdentityProvider):
    def __init__(self, w3, private_key):
        self.w3 = w3
        if private_key.startswith("::"):
            self.private_key = None
            self.address = None
            return
        self.set_secret(private_key)

    def set_secret(self, private_key):
        self.private_key = normalize_private_key(private_key)
        self.address = get_address_from_private(self.private_key)

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        raw_transaction = sign_transaction_with_private_key(
            self.w3, self.private_key, transaction)
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_solidity_keccak(self, message):
        return sign_message_with_private_key(self.w3, self.private_key, message)


class KeyStoreIdentityProvider(IdentityProvider):
    def __init__(self, w3, path_to_keystore):
        self.w3 = w3
        try:
            with open(path_to_keystore) as keyfile:
                encrypted_key = keyfile.read()
                self.address = self.w3.to_checksum_address(
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

    def sign_message_after_solidity_keccak(self, message):

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
        txn_hash = self.w3.eth.send_transaction(transaction)
        return send_and_wait_for_transaction_receipt(txn_hash, self.w3)

    def sign_message_after_solidity_keccak(self, message):
        return self.w3.eth.sign(self.get_address(), message)


class MnemonicIdentityProvider(IdentityProvider):
    def __init__(self, w3, mnemonic, index):
        self.w3 = w3
        self.index = index
        if mnemonic.startswith("::"):
            self.private_key = None
            self.address = None
            return
        self.set_secret(mnemonic)

    def set_secret(self, mnemonic):
        Account.enable_unaudited_hdwallet_features()
        account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{self.index}")
        self.private_key = account.key.hex()
        self.address = account.address

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        raw_transaction = sign_transaction_with_private_key(
            self.w3, self.private_key, transaction)
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_solidity_keccak(self, message):
        return sign_message_with_private_key(self.w3, self.private_key, message)


class TrezorIdentityProvider(IdentityProvider):
    def __init__(self, w3, index):
        self.w3 = w3
        self.index = index

        try:
            transport = get_transport()
        except Exception as e:
            raise RuntimeError("No Trezor device found. Ensure it is connected and unlocked.") from e

        self.client = TrezorClient(transport, ui = ui.ClickUI())
        self.path = tools.parse_path(f"m/44'/60'/0'/0/{index}")

        self.address = self.w3.to_checksum_address(
            ethereum.get_address(self.client, self.path)
        )

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        print("Sending transaction to trezor for signature...\n", file = out_f)

        tx_data = transaction.get("data", b"")
        if isinstance(tx_data, str) and tx_data.startswith("0x"):
            tx_data = bytes.fromhex(tx_data[2:])

        tx_to = transaction["to"]
        if isinstance(tx_to, str) and tx_to.startswith("0x"):
            tx_to = bytes.fromhex(tx_to[2:])

        chain_id = int(transaction.get("chainId", self.w3.eth.chain_id))

        v, r, s = ethereum.sign_tx(
            self.client,
            n = self.path,
            nonce = int(transaction["nonce"]),
            gas_price = int(transaction["gasPrice"]),
            gas_limit = int(transaction["gas"]),
            to = transaction["to"],  # Trezorlib handles "0x" strings fine here
            value = int(transaction["value"]),
            data = tx_data,
            chain_id = chain_id
        )
        r = int.from_bytes(r, byteorder = "big")
        s = int.from_bytes(s, byteorder = "big")

        signed_tx = Transaction(
            nonce = int(transaction["nonce"]),
            gasPrice = int(transaction["gasPrice"]),
            gas = int(transaction["gas"]),
            to = tx_to,
            value = int(transaction["value"]),
            data = tx_data,
            v = v,
            r = r,
            s = s
        )

        raw_transaction = rlp.encode(signed_tx)

        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_solidity_keccak(self, message):
        result = ethereum.sign_message(self.client, self.path, message)
        return result.signature


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
                "Received commException from Ledger. Are you sure your device is plugged in?")

        self.dongle_path = parse_bip32_path("44'/60'/0'/0/{}".format(index))

        apdu = LedgerIdentityProvider.GET_ADDRESS_OP
        apdu += bytearray([len(self.dongle_path) + 1,
                           int(len(self.dongle_path) / 4)]) + self.dongle_path
        try:
            result = self.dongle.exchange(apdu)
        except CommException:
            raise RuntimeError("Received commException from Ledger. Are you sure your device is unlocked and the "
                               "Ethereum app is running?")

        offset = 1 + result[0]
        self.address = self.w3.to_checksum_address(bytes(result[offset + 1: offset + 1 + result[offset]])
                                                   .decode("utf-8"))

    def get_address(self):
        return self.address

    def transact(self, transaction, out_f):
        chain_id = int(transaction.get("chainId", self.w3.eth.chain_id))

        tx_obj = Transaction(
            nonce = int(transaction["nonce"]),
            gasPrice = int(transaction["gasPrice"]),
            gas = int(transaction["gas"]),
            to = bytes.fromhex(transaction["to"][2:]),
            value = int(transaction["value"]),
            data = bytes.fromhex(transaction["data"][2:]),
            v = chain_id,
            r = 0,
            s = 0
        )

        encoded_tx = rlp.encode(tx_obj)

        overflow = len(self.dongle_path) + 1 + len(encoded_tx) - 255

        if overflow > 0:
            encoded_tx_part, remaining_tx = encoded_tx[:-overflow], encoded_tx[-overflow:]
        else:
            encoded_tx_part = encoded_tx
            remaining_tx = b""

        apdu = LedgerIdentityProvider.SIGN_TX_OP
        apdu += bytearray([len(self.dongle_path) + 1 + len(encoded_tx_part), int(len(self.dongle_path) / 4)])
        apdu += self.dongle_path + encoded_tx_part

        try:
            print("Sending transaction to Ledger for signature...\n", file = out_f)
            result = self.dongle.exchange(apdu)

            while remaining_tx:
                overflow = len(remaining_tx) - 255
                if overflow > 0:
                    encoded_tx_part, remaining_tx = remaining_tx[:-overflow], remaining_tx[-overflow:]
                else:
                    encoded_tx_part = remaining_tx
                    remaining_tx = b""

                apdu = LedgerIdentityProvider.SIGN_TX_OP_CONT
                apdu += bytearray([len(encoded_tx_part)])
                apdu += encoded_tx_part
                result = self.dongle.exchange(apdu)

        except CommException as e:
            if e.sw == 0x6985:  # Common status word for user denial
                raise RuntimeError("Transaction denied from Ledger by user")
            raise RuntimeError(f"Ledger error: {e.sw:x}")

        v_raw = result[0]

        if v_raw <= 1:
            v_parity = v_raw
        else:
            v_parity = 1 - (v_raw % 2)

        v = (chain_id * 2 + 35) + v_parity

        r = int.from_bytes(result[1:33], byteorder = "big")
        s = int.from_bytes(result[33:65], byteorder = "big")

        signed_tx = Transaction(
            nonce = tx_obj.nonce,
            gasPrice = tx_obj.gasPrice,
            gas = tx_obj.gas,
            to = tx_obj.to,
            value = tx_obj.value,
            data = tx_obj.data,
            v = v,
            r = r,
            s = s
        )

        raw_transaction = rlp.encode(signed_tx)
        return send_and_wait_for_transaction(raw_transaction, self.w3, out_f)

    def sign_message_after_solidity_keccak(self, message):
        apdu = LedgerIdentityProvider.SIGN_MESSAGE_OP
        apdu += bytearray([len(self.dongle_path) + 1 +
                           len(message) + 4, int(len(self.dongle_path) / 4)])
        apdu += self.dongle_path + struct.pack(">I", len(message)) + message
        try:
            result = self.dongle.exchange(apdu)
        except CommException:
            raise RuntimeError("Received commException from Ledger. Are you sure your device is unlocked and the "
                               "Ethereum app is running?")

        return result[1:] + result[0:1]


def send_and_wait_for_transaction_receipt(txn_hash, w3):
    # Wait for transaction to be mined
    receipt = dict()
    while not receipt:
        time.sleep(1)
        try:
            receipt = w3.eth.get_transaction_receipt(txn_hash)
            if receipt and "blockHash" in receipt and receipt["blockHash"] is None:
                receipt = dict()
        except:
            receipt = dict()
    return receipt


def send_and_wait_for_transaction(raw_transaction, w3, out_f):
    print("Submitting transaction...\n", file=out_f)
    txn_hash = w3.eth.send_raw_transaction(raw_transaction)
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


def get_kws_for_identity_type(identity_type: str) -> dict:
    secret = True
    plaintext = False

    result = {}

    if identity_type == "rpc":
        result["network"] = plaintext
    elif identity_type == "mnemonic":
        result["mnemonic"] = secret
    elif identity_type == "key":
        result["private_key"] = secret
    elif identity_type == "keystore":
        result["keystore_path"] = plaintext
    elif identity_type in ["trezor", "ledger"]:
        # empty dict
        pass
    else:
        raise RuntimeError(
            "unrecognized identity_type {}".format(identity_type))

    return result

def get_identity_types():
    # temporary fully removed: trezor
    return ["rpc", "mnemonic", "key", "trezor", "ledger", "keystore"]


def sign_transaction_with_private_key(w3, private_key, transaction):
    return w3.eth.account.sign_transaction(transaction, private_key).raw_transaction


def sign_message_with_private_key(w3, private_key, message):
    message_encoded = encode_defunct(primitive = message)
    signed_message = w3.eth.account.sign_message(message_encoded, private_key)

    return signed_message.signature


def unlock_keystore_with_password(w3, path_to_keystore):
    password = getpass.getpass("Password : ") or ""
    with open(path_to_keystore) as keyfile:
        encrypted_key = keyfile.read()
        return w3.eth.account.decrypt(encrypted_key, password)
