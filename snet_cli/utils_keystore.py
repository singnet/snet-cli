import os
import sys
import binascii
import struct
from math import ceil

import pbkdf2
from Crypto.Hash import keccak
from eth_utils import encode_hex
from eth_utils import decode_hex


from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util import Counter

# TODO: make it compatible!
try:
    scrypt = __import__('scrypt')
except ImportError:
    sys.stderr.write("""
Failed to import scrypt. This is not a fatal error but does
mean that you cannot create or decrypt privkey jsons that use
scrypt
""")
    scrypt = None


SCRYPT_CONSTANTS = {
    "n": 262144,
    "r": 1,
    "p": 8,
    "dklen": 32
}

PBKDF2_CONSTANTS = {
    "prf": "hmac-sha256",
    "dklen": 32,
    "c": 262144
}


def aes_ctr_encrypt(text, key, params):
    iv = big_endian_to_int(decode_hex(params["iv"]))
    ctr = Counter.new(128, initial_value=iv, allow_wraparound=True)
    mode = AES.MODE_CTR
    encryptor = AES.new(key, mode, counter=ctr)
    return encryptor.encrypt(text)


def aes_ctr_decrypt(text, key, params):
    iv = big_endian_to_int(decode_hex(params["iv"]))
    ctr = Counter.new(128, initial_value=iv, allow_wraparound=True)
    mode = AES.MODE_CTR
    encryptor = AES.new(key, mode, counter=ctr)
    return encryptor.decrypt(text)


def aes_mkparams():
    return {"iv": encode_hex(os.urandom(16))}


ciphers = {
    "aes-128-ctr": {
        "encrypt": aes_ctr_encrypt,
        "decrypt": aes_ctr_decrypt,
        "mkparams": aes_mkparams
    }
}


def mk_scrypt_params():
    params = SCRYPT_CONSTANTS.copy()
    params['salt'] = encode_hex(os.urandom(16))
    return params


def scrypt_hash(val, params):
    return scrypt.hash(str(val), decode_hex(params["salt"]), params["n"],
                       params["r"], params["p"], params["dklen"])


def mk_pbkdf2_params():
    params = PBKDF2_CONSTANTS.copy()
    params['salt'] = encode_hex(os.urandom(16))
    return params


def pbkdf2_hash(val, params):
    assert params["prf"] == "hmac-sha256"
    return pbkdf2.PBKDF2(val, decode_hex(params["salt"]), params["c"],
                         SHA256).read(params["dklen"])


kdfs = {
    "pbkdf2": {
        "calc": pbkdf2_hash,
        "mkparams": mk_pbkdf2_params
    }
}


if scrypt is not None:
    kdfs["scrypt"] = {
        "calc": scrypt_hash,
        "mkparams": mk_scrypt_params
    }


ciphers = {
    "aes-128-ctr": {
        "encrypt": aes_ctr_encrypt,
        "decrypt": aes_ctr_decrypt,
        "mkparams": aes_mkparams
    }
}


if sys.version_info.major == 2:
    def int_to_big_endian(value):
        cs = []
        while value > 0:
            cs.append(chr(value % 256))
            value /= 256
        s = ''.join(reversed(cs))
        return s

    def big_endian_to_int(value):
        if len(value) == 1:
            return ord(value)
        elif len(value) <= 8:
            return struct.unpack('>Q', value.rjust(8, b'\x00'))[0]
        else:
            return int(encode_hex(value), 16)

if sys.version_info.major == 3:

    def int_to_big_endian(value):
        byte_length = ceil(value.bit_length() // 8)
        return (value).to_bytes(byte_length, byteorder='big')

    def big_endian_to_int(value):
        return int.from_bytes(value, byteorder='big')


# Utility functions (done separately from utils so as to make this a
# standalone file)
def sha3_256(x): return keccak.new(digest_bits=256, data=x)


def sha3(seed):
    return sha3_256(seed).digest()


def decode_keystore_json(jsondata, pw):
    # Get KDF function and parameters
    if "crypto" in jsondata:
        cryptdata = jsondata["crypto"]
    elif "Crypto" in jsondata:
        cryptdata = jsondata["Crypto"]
    else:
        raise Exception("JSON data must contain \"crypto\" object")
    kdfparams = cryptdata["kdfparams"]
    kdf = cryptdata["kdf"]
    if cryptdata["kdf"] not in kdfs:
        raise Exception("Hash algo %s not supported" % kdf)
    kdfeval = kdfs[kdf]["calc"]
    # Get cipher and parameters
    cipherparams = cryptdata["cipherparams"]
    cipher = cryptdata["cipher"]
    if cryptdata["cipher"] not in ciphers:
        raise Exception("Encryption algo %s not supported" % cipher)
    decrypt = ciphers[cipher]["decrypt"]
    # Compute the derived key
    derivedkey = kdfeval(pw, kdfparams)
    assert len(derivedkey) >= 32, \
        "Derived key must be at least 32 bytes long"
    # print(b'derivedkey: ' + encode_hex(derivedkey))
    enckey = derivedkey[:16]
    # print(b'enckey: ' + encode_hex(enckey))
    ctext = decode_hex(cryptdata["ciphertext"])
    # Decrypt the ciphertext
    o = decrypt(ctext, enckey, cipherparams)
    # Compare the provided MAC with a locally computed MAC
    # print(b'macdata: ' + encode_hex(derivedkey[16:32] + ctext))
    mac1 = sha3(derivedkey[16:32] + ctext)
    mac2 = decode_hex(cryptdata["mac"])
    if mac1 != mac2:
        raise ValueError("MAC mismatch. Password incorrect?")
    return o
