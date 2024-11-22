from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path
import sys

from snet.cli.utils.config import encrypt_secret

default_snet_folder = Path("~").expanduser().joinpath(".snet")
DEFAULT_NETWORK = "sepolia"


class Config(ConfigParser):
    def __init__(self, _snet_folder=default_snet_folder, sdk_config=None):
        super(Config, self).__init__(interpolation=ExtendedInterpolation(), delimiters=("=",))
        self._config_file = _snet_folder.joinpath("config")
        self.sdk_config = sdk_config
        self.is_sdk = True if sdk_config else False
        if self._config_file.exists():
            with open(self._config_file) as f:
                self.read_file(f)
        else:
            self.create_default_config()

    def get_session_network_name(self):
        session_network = self["session"]["network"]
        self._check_section("network.%s" % session_network)
        return session_network

    def safe_get_session_identity_network_names(self):
        if "identity" not in self["session"]:
            first_identity_message_and_exit(is_sdk=self.is_sdk)

        session_identity = self["session"]["identity"]
        self._check_section("identity.%s" % session_identity)

        session_network = self.get_session_network_name()

        network = self._get_identity_section(session_identity).get("network")
        if network and network != session_network:
            raise Exception("Your session identity '%s' is bind to network '%s', which is different from your"
                            " session network '%s', please switch identity or network" % (
                            session_identity, network, session_network))
        return session_identity, session_network

    def set_session_network(self, network, out_f):
        self._set_session_network(network, out_f)
        if "identity" in self["session"]:
            session_identity = self["session"]["identity"]
            identity_network = self._get_identity_section(session_identity).get("network")
            if identity_network and identity_network != network:
                print("Your new session network '%s' is incompatible with your current session identity '%s' "
                      "(which is bind to network '%s'), please switch your identity" % (
                      network, session_identity, identity_network), file=out_f)

    def _set_session_network(self, network, out_f):
        if network not in self.get_all_networks_names():
            raise Exception("Network %s is not in config" % network)
        print("Switch to network: %s" % network, file=out_f)
        self["session"]["network"] = network
        self._persist()

    def set_session_identity(self, identity, out_f):
        if identity not in self.get_all_identities_names():
            raise Exception('Identity "%s" is not in config' % identity)
        network = self._get_identity_section(identity).get("network")
        if network:
            print('Identity "%s" is bind to network "%s"' % (identity, network), file=out_f)
            self._set_session_network(network, out_f)
        else:
            print(
                'Identity "%s" is not bind to any network. You should switch network manually if you need.' % identity,
                file=out_f)
        print("Switch to identity: %s" % (identity), file=out_f)
        self["session"]["identity"] = identity
        self._persist()

    # session is the union of session.identity + session.network + default_ipfs_endpoint
    # if value is presented in both session.identity and session.network we get it from session.identity (can happen only for default_eth_rpc_endpoint)
    def get_session_field(self, key, exception_if_not_found=True):
        session_identity, session_network = self.safe_get_session_identity_network_names()

        rez_identity = self._get_identity_section(session_identity).get(key)
        rez_network = self._get_network_section(session_network).get(key)

        rez_ipfs = None
        if key == "default_ipfs_endpoint":
            rez_ipfs = self.get_ipfs_endpoint()

        rez = rez_identity or rez_network or rez_ipfs
        if not rez and exception_if_not_found:
            raise Exception("Cannot find %s in the session.identity and in the session.network" % key)
        return rez

    def set_session_field(self, key, value, out_f):
        if key == "default_ipfs_endpoint":
            self.set_ipfs_endpoint(value)
            print("set default_ipfs_endpoint=%s" % value, file=out_f)
        elif key == "filecoin_api_key":
            self.set_filecoin_key(value)
            print("set filecoin_api_key=%s" % value, file=out_f)
        elif key in get_session_network_keys():
            session_network = self.get_session_network_name()
            self.set_network_field(session_network, key, value)
            print("set {}={} for network={}".format(key, value, session_network), file=out_f)
        elif key in get_session_identity_keys():
            session_identity, _ = self.safe_get_session_identity_network_names()
            self.set_identity_field(session_identity, key, value)
            print("set {}={} for identity={}".format(key, value, session_identity), file=out_f)
        else:
            all_keys = get_session_network_keys() + get_session_identity_keys() + ["default_ipfs_endpoint"]
            raise Exception("key {} not in {}".format(key, all_keys))

    def unset_session_field(self, key, out_f):
        if key in get_session_network_keys_removable():
            print("unset %s from network %s" % (key, self["session"]["network"]), file=out_f)
            if key == "filecoin_api_key":
                self.unset_filecoin_key()
            else:
                del self._get_network_section(self["session"]["network"])[key]
        self._persist()

    def session_to_dict(self):
        session_identity, session_network = self.safe_get_session_identity_network_names()

        show = {"session", "network.%s" % session_network, "identity.%s" % session_identity, "ipfs", "filecoin"}
        response = {f: dict(self[f]) for f in show}
        return response

    def add_network(self, network, rpc_endpoint, default_gas_price):
        network_section = "network.%s" % network
        if network_section in self:
            raise Exception("Network section %s already exists in config" % network)

        self[network_section] = {}
        self[network_section]["default_eth_rpc_endpoint"] = str(rpc_endpoint)
        # TODO: find solution with default gas price
        self[network_section]["default_gas_price"] = str(default_gas_price)
        self._persist()

    def set_network_field(self, network, key, value):
        self._get_network_section(network)[key] = str(value)
        self._persist()

    def add_identity(self, identity_name, identity, out_f=sys.stdout, password=None):
        identity_section = "identity.%s" % identity_name
        if identity_section in self:
            raise Exception("Identity section %s already exists in config" % identity_section)
        if "network" in identity and identity["network"] not in self.get_all_networks_names():
            raise Exception("Network %s is not in config" % identity["network"])

        if password:
            if "mnemonic" in identity:
                identity["mnemonic"] = encrypt_secret(identity["mnemonic"], password)
            elif "private_key" in identity:
                identity["private_key"] = encrypt_secret(identity["private_key"], password)

        self[identity_section] = identity
        self._persist()
        # switch to it, if it was the first identity
        if len(self.get_all_identities_names()) == 1:
            print("You've just added your first identity %s. We will automatically switch to it!" % identity_name)
            self.set_session_identity(identity_name, out_f)

    def set_identity_field(self, identity, key, value):
        self._get_identity_section(identity)[key] = str(value)
        self._persist()

    def _get_network_section(self, network):
        """ return section for network or identity """
        return self["network.%s" % network]

    def _get_identity_section(self, identity):
        """ return section for the specific identity """
        return self["identity.%s" % identity]

    def get_ipfs_endpoint(self):
        return self["ipfs"]["default_ipfs_endpoint"]

    def set_ipfs_endpoint(self, ipfs_endpoint):
        self["ipfs"]["default_ipfs_endpoint"] = ipfs_endpoint
        self._persist()

    def get_filecoin_key(self):
        if "filecoin" not in self or not self["filecoin"].get("filecoin_api_key"):
            raise Exception("Use [snet set filecoin_api_key <YOUR_LIGHTHOUSE_API_KEY>] to set filecoin key")
        return self["filecoin"]["filecoin_api_key"]

    def set_filecoin_key(self, filecoin_key: str):
        if "filecoin" not in self:
            self["filecoin"] = {"filecoin_api_key": ""}
        self["filecoin"]["filecoin_api_key"] = filecoin_key
        self._persist()

    def unset_filecoin_key(self):
        del self["filecoin"]["filecoin_api_key"]
        self._persist()

    def get_all_identities_names(self):
        return [x[len("identity."):] for x in self.sections() if x.startswith("identity.")]

    def get_all_networks_names(self):
        return [x[len("network."):] for x in self.sections() if x.startswith("network.")]

    def delete_identity(self, identity_name):
        if identity_name not in self.get_all_identities_names():
            raise Exception("identity_name {} does not exist".format(identity_name))

        session_identity, _ = self.safe_get_session_identity_network_names()
        if identity_name == session_identity:
            raise Exception("identity_name {} is in use".format(identity_name))
        self.remove_section("identity.{}".format(identity_name))
        self._persist()

    def create_default_config(self):
        """ Create default configuration if config file does not exist """
        # make config directory with the minimal possible permission
        self._config_file.parent.mkdir(mode=0o700, exist_ok=True)
        self["network.mainnet"] = {
            "default_eth_rpc_endpoint": "https://mainnet.infura.io/v3/09027f4a13e841d48dbfefc67e7685d5"
        }
        self["network.sepolia"] = {
            "default_eth_rpc_endpoint": "https://sepolia.infura.io/v3/09027f4a13e841d48dbfefc67e7685d5",
        }
        self["ipfs"] = {"default_ipfs_endpoint": "/dns/ipfs.singularitynet.io/tcp/80/"}
        self["filecoin"] = {"filecoin_api_key": ""}
        network = self.get_param_from_sdk_config("network")
        if network:
            if network not in self.get_all_networks_names():
                raise Exception("Network '%s' is not in config" % network)
            self["session"] = {"network": network}
        else:
            self["session"] = {"network": DEFAULT_NETWORK}
        identity_name = self.get_param_from_sdk_config("identity_name")
        identity_type = self.get_param_from_sdk_config("identity_type")
        if identity_name and identity_type:
            identity = self.setup_identity()
            self.add_identity(identity_name, identity)
        self._persist()
        print("We've created configuration file with default values in: %s\n" % str(self._config_file))

    def _check_section(self, s):
        if s not in self:
            raise Exception("Config error, section %s is absent" % s)

    def _persist(self):
        with open(self._config_file, "w") as f:
            self.write(f)
        self._config_file.chmod(0o600)

    def get_param_from_sdk_config(self, param: str, alternative=None):
        if self.sdk_config:
            return self.sdk_config.get(param, alternative)
        return None

    def setup_identity(self):
        identity_type = self.get_param_from_sdk_config("identity_type")
        private_key = self.get_param_from_sdk_config("private_key")
        default_wallet_index = self.get_param_from_sdk_config("wallet_index", 0)
        if not identity_type:
            raise Exception("identity_type not passed")
        if identity_type == "key":
            identity = {
                "identity_type": "key",
                "private_key": private_key,
                "default_wallet_index": default_wallet_index
            }
        # TODO: logic for other identity_type
        else:
            print("\nThe identity_type parameter value you passed is not supported "
              "by the sdk at this time.\n")
            print("The available identity types are:\n"
                  "    - 'key' (uses a required hex-encoded private key for signing)\n\n")
            exit(1)
        return identity


def first_identity_message_and_exit(is_sdk=False):
    if is_sdk:
        print("\nPlease create your first identity by passing the 'identity_name' "
              "and 'identity_type' parameters in SDK config.\n")
        print("The available identity types are:\n"
              "    - 'key' (uses a required hex-encoded private key for signing)\n\n")
    else:
        print("\nPlease create your first identity by running 'snet identity create'.\n\n")
        print("The available identity types are:\n"
              "    - 'rpc' (yields to a required ethereum json-rpc endpoint for signing using a given wallet\n"
              "          index)\n"
              "    - 'mnemonic' (uses a required bip39 mnemonic for HDWallet/account derivation and signing\n"
              "          using a given wallet index)\n"
              "    - 'key' (uses a required hex-encoded private key for signing)\n"
              "    - 'ledger' (yields to a required ledger nano s device for signing using a given wallet\n"
              "          index)\n"
              "    - 'trezor' (yields to a required trezor device for signing using a given wallet index)\n"
              "\n")
    exit(1)


def get_session_identity_keys():
    return ["default_wallet_index"]


def get_session_network_keys():
    return ["current_registry_at", "current_multipartyescrow_at", "current_singularitynettoken_at",
            "default_eth_rpc_endpoint"]


def get_session_network_keys_removable():
    return ["current_registry_at", "current_multipartyescrow_at", "current_singularitynettoken_at", "filecoin_api_key"]


def get_session_keys():
    return get_session_network_keys() + get_session_identity_keys() + ["default_ipfs_endpoint"] + ["filecoin_api_key"]
