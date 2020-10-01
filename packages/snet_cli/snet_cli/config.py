from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path

default_snet_folder = Path("~").expanduser().joinpath(".snet")


class Config(ConfigParser):
    def __init__(self, _snet_folder=default_snet_folder):
        super(Config, self).__init__(interpolation=ExtendedInterpolation(), delimiters=("=",))
        self._config_file = _snet_folder.joinpath("config")
        if (self._config_file.exists()):
            with open(self._config_file) as f:
                self.read_file(f)
        else:
            self.create_default_config()

    def get_session_network_name(self):
        session_network = self["session"]["network"]
        self._check_section("network.%s" % session_network)
        return session_network

    def safe_get_session_identity_network_names(self):
        if ("identity" not in self["session"]):
            first_identity_message_and_exit()

        session_identity = self["session"]["identity"]
        self._check_section("identity.%s" % session_identity)

        session_network = self.get_session_network_name()

        network = self._get_identity_section(session_identity).get("network")
        if (network and network != session_network):
            raise Exception("Your session identity '%s' is bind to network '%s', which is different from your"
                            " session network '%s', please switch identity or network" % (
                            session_identity, network, session_network))
        return session_identity, session_network

    def set_session_network(self, network, out_f):
        self._set_session_network(network, out_f)
        if ("identity" in self["session"]):
            session_identity = self["session"]["identity"]
            identity_network = self._get_identity_section(session_identity).get("network")
            if (identity_network and identity_network != network):
                print("Your new session network '%s' is incompatible with your current session identity '%s' "
                      "(which is bind to network '%s'), please switch your identity" % (
                      network, session_identity, identity_network), file=out_f);

    def _set_session_network(self, network, out_f):
        if (network not in self.get_all_networks_names()):
            raise Exception("Network %s is not in config" % network)
        print("Switch to network: %s" % network, file=out_f)
        self["session"]["network"] = network
        self._persist()

    def set_session_identity(self, identity, out_f):
        if (identity not in self.get_all_identities_names()):
            raise Exception('Identity "%s" is not in config' % identity)
        network = self._get_identity_section(identity).get("network")
        if (network):
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
        if (key == "default_ipfs_endpoint"):
            rez_ipfs = self.get_ipfs_endpoint()

        rez = rez_identity or rez_network or rez_ipfs
        if (not rez and exception_if_not_found):
            raise Exception("Cannot find %s in the session.identity and in the session.network" % key)
        return rez

    def set_session_field(self, key, value, out_f):
        if (key == "default_ipfs_endpoint"):
            self.set_ipfs_endpoint(value)
            print("set default_ipfs_endpoint=%s" % value, file=out_f)
        elif (key in get_session_network_keys()):
            session_network = self.get_session_network_name();
            self.set_network_field(session_network, key, value)
            print("set {}={} for network={}".format(key, value, session_network), file=out_f)
        elif (key in get_session_identity_keys()):
            session_identity, _ = self.safe_get_session_identity_network_names()
            self.set_identity_field(session_identity, key, value)
            print("set {}={} for identity={}".format(key, value, session_identity), file=out_f)
        else:
            all_keys = get_session_network_keys() + get_session_identity_keys() + ["default_ipfs_endpoint"]
            raise Exception("key {} not in {}".format(key, all_keys))

    def unset_session_field(self, key, out_f):
        if (key in get_session_network_keys_removable()):
            print("unset %s from network %s" % (key, self["session"]["network"]), file=out_f)
            del self._get_network_section(self["session"]["network"])[key]
        self._persist()

    def session_to_dict(self):
        session_identity, session_network = self.safe_get_session_identity_network_names()

        show = {"session", "network.%s" % session_network, "identity.%s" % session_identity, "ipfs"}
        rez = {f: dict(self[f]) for f in show}
        return rez

    def add_network(self, network, rpc_endpoint, default_gas_price):
        network_section = "network.%s" % network
        if (network_section in self):
            raise Exception("Network section %s already exists in config" % network)

        self[network_section] = {}
        self[network_section]["default_eth_rpc_endpoint"] = str(rpc_endpoint)
        self[network_section]["default_gas_price"] = str(default_gas_price)
        self._persist()

    def set_network_field(self, network, key, value):
        self._get_network_section(network)[key] = str(value)
        self._persist()

    def add_identity(self, identity_name, identity, out_f):
        identity_section = "identity.%s" % identity_name
        if (identity_section in self):
            raise Exception("Identity section %s already exists in config" % identity_section)
        if ("network" in identity and identity["network"] not in self.get_all_networks_names()):
            raise Exception("Network %s is not in config" % identity["network"])
        self[identity_section] = identity
        self._persist()
        # switch to it, if it was the first identity
        if (len(self.get_all_identities_names()) == 1):
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

    def get_all_identities_names(self):
        return [x[len("identity."):] for x in self.sections() if x.startswith("identity.")]

    def get_all_networks_names(self):
        return [x[len("network."):] for x in self.sections() if x.startswith("network.")]

    def delete_identity(self, identity_name):
        if (identity_name not in self.get_all_identities_names()):
            raise Exception("identity_name {} does not exist".format(identity_name))

        session_identity, _ = self.safe_get_session_identity_network_names()
        if (identity_name == session_identity):
            raise Exception("identity_name {} is in use".format(identity_name))
        self.remove_section("identity.{}".format(identity_name))
        self._persist()

    def create_default_config(self):
        """ Create default configuration if config file does not exist """
        # make config directory with the minimal possible permission
        self._config_file.parent.mkdir(mode=0o700, exist_ok=True)
        self["network.kovan"] = {
            "default_eth_rpc_endpoint": "https://kovan.infura.io/v3/09027f4a13e841d48dbfefc67e7685d5",
            "default_gas_price": "medium"}
        self["network.mainnet"] = {
            "default_eth_rpc_endpoint": "https://mainnet.infura.io/v3/09027f4a13e841d48dbfefc67e7685d5",
            "default_gas_price": "medium"}
        self["network.ropsten"] = {
            "default_eth_rpc_endpoint": "https://ropsten.infura.io/v3/09027f4a13e841d48dbfefc67e7685d5",
            "default_gas_price": "medium"}
        self["network.rinkeby"] = {
            "default_eth_rpc_endpoint": "https://rinkeby.infura.io/v3/09027f4a13e841d48dbfefc67e7685d5",
            "default_gas_price": "medium"}
        self["ipfs"] = {"default_ipfs_endpoint": "http://ipfs.singularitynet.io:80"}
        self["session"] = {
            "network": "kovan"}
        self._persist()
        print("We've created configuration file with default values in: %s\n" % str(self._config_file))

    def _check_section(self, s):
        if (s not in self):
            raise Exception("Config error, section %s is absent" % s)

    def _persist(self):
        with open(self._config_file, "w") as f:
            self.write(f)
        self._config_file.chmod(0o600)


def first_identity_message_and_exit():
    print("\nPlease create your first identity by running 'snet identity create'.\n\n"
          "The available identity types are:\n"
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
    return ["default_gas_price", "current_registry_at", "current_multipartyescrow_at", "current_singularitynettoken_at",
            "default_eth_rpc_endpoint"]


def get_session_network_keys_removable():
    return ["default_gas_price", "current_registry_at", "current_multipartyescrow_at", "current_singularitynettoken_at"]


def get_session_keys():
    return get_session_network_keys() + get_session_identity_keys() + ["default_ipfs_endpoint"]
