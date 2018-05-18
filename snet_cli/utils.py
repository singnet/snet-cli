
import web3

from snet_cli.identity import RpcIdentityProvider, MnemonicIdentityProvider, TrezorIdentityProvider, \
    LedgerIdentityProvider, KeyIdentityProvider


class DefaultAttributeObject(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)

    def getstring(self, item):
        return getattr(self, item)

    def getint(self, item):
        if getattr(self, item) is None:
            return None
        return int(getattr(self, item))

    def getfloat(self, item):
        if getattr(self, item) is None:
            return None
        return float(getattr(self, item))

    def getboolean(self, item):
        if getattr(self, item) is None:
            return None
        i = self.getstring(item)
        if i in ["yes", "on", "true", "True", "1"]:
            return True
        return False

    def __getattr__(self, item):
        return self.__dict__.get(item, None)

    def __repr__(self):
        return self.__dict__.__repr__()

    def __str__(self):
        return self.__dict__.__str__()


def get_identity(w3, session, args):
    if session.identity is None:
        pass
    if session.identity.identity_type == "rpc":
        return RpcIdentityProvider(w3, args.wallet_index or session.getint("default_wallet_index"))
    if session.identity.identity_type == "mnemonic":
        return MnemonicIdentityProvider(w3, session.identity.mnemonic,
                                        args.wallet_index or session.getint("default_wallet_index"))
    if session.identity.identity_type == "trezor":
        return TrezorIdentityProvider(w3, args.wallet_index or session.getint("default_wallet_index"))
    if session.identity.identity_type == "ledger":
        return LedgerIdentityProvider(w3, args.wallet_index or session.getint("default_wallet_index"))
    if session.identity.identity_type == "key":
        return KeyIdentityProvider(w3, session.identity.private_key)


def get_web3(rpc_endpoint):
    if rpc_endpoint.startswith("ws:"):
        provider = web3.WebsocketProvider(rpc_endpoint)
    else:
        provider = web3.HTTPProvider(rpc_endpoint)

    return web3.Web3(provider)


def serializable(o):
    if isinstance(o, bytes):
        return o.hex()
    else:
        return o.__dict__


def type_converter(t):
    if "int" in t:
        return lambda x: web3.Web3.toInt(text=x)
    elif "byte" in t:
        return lambda x: web3.Web3.toBytes(text=x) if not x.startswith("0x") else web3.Web3.toBytes(hexstr=x)
    elif "address" in t:
        return web3.Web3.toChecksumAddress
    else:
        return str
