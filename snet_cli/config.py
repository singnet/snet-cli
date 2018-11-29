from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path

default_snet_folder = Path("~").expanduser().joinpath(".snet")

class Config(ConfigParser):
    def __init__(self, _snet_folder = default_snet_folder):
        super(Config, self).__init__(interpolation=ExtendedInterpolation(), delimiters=("=",))
        self._config_file = _snet_folder.joinpath("config")
        self.create_default_if_not_exists()

        with open(self._config_file) as f:
            self.read_file(f)

    # get identity_name of the current identity
    def get_session_identity_name(self):
        if ("identity" not in self["session"]):
            first_identity_message_and_exit(1)
        n = self["session"]["identity"]
        self._check_section("identity.%s"%n)
        return n

    # get network name of the current network
    def get_session_network_name(self):
        n = self["session"]["network"]
        self._check_section("network.%s"%n)
        return n

    def set_session_network(self, network):
        if (network not in self.get_all_networks_names()):
            raise Exception("Network %s is not in config"%network)
        self["session"]["network"] = network
        self._persist()

    def set_session_identity(self, identity):
        if (identity not in self.get_all_identies_names()):
            raise Exception("Identity %s is not in config"%identity)
        self["session"]["identity"] = identity
        self._persist()


    # session is the union of session.identity + session.network + default_ipfs_endpoint
    # if value is presented in both session.identity and session.network we get it from session.identity (can happen only for default_eth_rpc_endpoint)
    def get_session_field(self, key, exception_if_not_found = True):
        session_identity = self.get_session_identity_name()
        session_network  = self["session"]["network"]

        rez_identity = self._get_identity_section(session_identity).get(key)
        rez_network  = self._get_network_section(session_network).get(key)

        rez_ipfs = None
        if (key == "default_ipfs_endpoint"):
            rez_ipfs = self.get_ipfs_endpoint()

        rez = rez_identity or rez_network or rez_ipfs
        if (not rez and exception_if_not_found):
            raise Exception("Cannot find %s in the session.identity and in the session.network"%key)
        return rez

    def set_session_field(self, key, value, out_f):
        session_identity = self.get_session_identity_name()
        session_network  = self["session"]["network"]

        if (key in get_session_network_keys()):
            self.set_network_field(session_network, key, value)
            print("set {}={} for network={}".format(key, value, session_network),  file=out_f)
        elif (key in get_session_identity_keys()):
            self.set_identity_field(session_identity, key, value)
            print("set {}={} for identity={}".format(key, value, session_identity), file=out_f)
        elif (key == "default_ipfs_endpoint"):
            self.set_ipfs_endpoint(value)
            print("set default_ipfs_endpoint=%s"%value, file=out_f)
        else:
            all_keys = get_session_network_keys() + get_session_identity_keys() + ["default_ipfs_endpoint"]
            raise Exception("key {} not in {}".format(key, all_keys))

    def unset_session_field(self, key, out_f):
        if (key in get_session_network_keys_removable()):
            del self._get_network_section(self["session"]["network"])[key]
        self._persist()

    def session_to_dict(self):
        session_identity = self.get_session_identity_name()
        session_network  = self.get_session_network_name()
        show = {"session", "network.%s"%session_network, "identity.%s"%session_identity, "ipfs"}
        rez = { f:dict(self[f]) for f in show }
        return rez

    def add_network(self, network, rpc_endpoint, default_gas_price):
        network_section = "network.%s"%network
        if (network_section in self):
            raise Exception("Network section %s already exists in config"%network)

        self[network_section] = {}
        self[network_section]["default_eth_rpc_endpoint"] = str(rpc_endpoint)
        self[network_section]["default_gas_price"]        = str(default_gas_price)
        self._persist()

    def set_network_field(self, network, key, value):
        self._get_network_section(network)[key] = str(value)
        self._persist()

    def add_identity(self, identity_name, identity):
        identity_section = "identity.%s"%identity_name
        if (identity_section in self):
            raise Exception("Identity section %s already exists in config"%identity_section)
        self[identity_section] = identity
        self._persist()

    def set_identity_field(self, identity, key, value):
        self._get_identity_section(identity)[key] = str(value)
        self._persist()

    # return section for network or identity
    def _get_network_section(self, network):
        return self[ "network.%s"%network ]

    # return section for the specific identity
    def _get_identity_section(self, identity):
        return self[ "identity.%s"%identity ]

    def get_ipfs_endpoint(self):
        return self["ipfs"]["default_ipfs_endpoint"]

    def set_ipfs_endpoint(self, ipfs_endpoint):
        self["ipfs"]["default_ipfs_endpoint"] = ipfs_endpoint
        self._persist()

    def get_all_identies_names(self):
        return [x[len("identity."):] for x in self.sections() if x.startswith("identity.")]

    def get_all_networks_names(self):
        return [x[len("network."):] for x in self.sections() if x.startswith("network.")]

    def delete_identity(self, identity_name):
        if (identity_name not in self.config.get_all_identies_names()):
            raise Exception("identity_name {} does not exist".format(identity_name))
        if (identity_name == self.get_session_identity_name()):
            raise Exception("identity_name {} is in use".format(identity_name))
        self.remove_section("identity.{}".format(identity_name))
        self._persist()

    # create default configuration if config file is not exists
    def create_default_if_not_exists(self):
        if (not self._config_file.exists()):
            self._config_file.parent.mkdir(exist_ok=True)
            self["network.kovan"]   = {"default_eth_rpc_endpoint": "https://kovan.infura.io",   "default_gas_price" : "1000000000"}
            self["network.mainnet"] = {"default_eth_rpc_endpoint": "https://mainnet.infura.io", "default_gas_price" : "1000000000"}
            self["network.ropsten"] = {"default_eth_rpc_endpoint": "https://ropsten.infura.io", "default_gas_price" : "1000000000"}
            self["network.rinkeby"] = {"default_eth_rpc_endpoint": "https://rinkeby.infura.io", "default_gas_price" : "1000000000"}
            self["ipfs"] = {"default_ipfs_endpoint": "http://ipfs.singularitynet.io:80"}
            self["session"] = {
            "network": "kovan" }
            self._persist()
            print("We've created configuration file with dafault values in: %s"%str(self._config_file))
            first_identity_message_and_exit()

    def _check_section(self, s):
        if (s not in self):
            raise Exception("Config error, section %s is absent"%s)

    def _persist(self):
        with open(self._config_file, "w") as f:
            self.write(f)


def first_identity_message_and_exit(exit_code=0):
    print("\nPlease create your first identity by runing 'snet identity create'.\n\n"
          "The available identity types are:\n"
          "    - 'rpc' (yields to a required ethereum json-rpc endpoint for signing using a given wallet\n"
          "          index)\n"
          "    - 'mnemonic' (uses a required bip39 mnemonic for HDWallet/account derivation and signing\n"
          "          using a given wallet index)\n"
          "    - 'key' (uses a required hex-encoded private key for signing)\n"
          "    - 'ledger' (yields to a required ledger nano s device for signing using a given wallet\n"
          "          index)\n"
          "    - 'trezor' (yields to a required trezor device for signing using a given wallet index)\n"
          "\n");
    exit(exit_code);


def get_session_identity_keys():
    return ["default_wallet_index"]

def get_session_network_keys():
    return ["default_gas_price", "current_registry_at", "current_multipartyescrow_at", "current_singularitynettoken_at"]

def get_session_network_keys_removable():
    return ["default_gas_price", "current_registry_at", "current_multipartyescrow_at", "current_singularitynettoken_at"]


def get_session_keys():
    return get_session_network_keys() + get_session_identity_keys() + ["default_ipfs_endpoint"]
