from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path

conf = ConfigParser(interpolation=ExtendedInterpolation(), delimiters=("=",))
_snet_folder = Path("~").expanduser().joinpath(".snet")
_snet_folder.mkdir(exist_ok=True)


def persist():
    with open(_snet_folder.joinpath("config"), "w") as f:
        conf.write(f)


try:
    with open(_snet_folder.joinpath("config")) as f:
        conf.read_file(f)
    # Looking for IPFS at snet-cli config file (required)
    if "ipfs" not in conf:
        conf["ipfs"] = {"default_ipfs_endpoint": "http://ipfs.singularitynet.io:80"}
        persist()
except FileNotFoundError:
    conf["network.kovan"] = {"default_eth_rpc_endpoint": "https://kovan.infura.io"}
    conf["network.mainnet"] = {"default_eth_rpc_endpoint": "https://mainnet.infura.io"}
    conf["network.ropsten"] = {"default_eth_rpc_endpoint": "https://ropsten.infura.io"}
    conf["network.rinkeby"] = {"default_eth_rpc_endpoint": "https://rinkeby.infura.io"}
    conf["ipfs"] = {"default_ipfs_endpoint": "http://ipfs.singularitynet.io:80"}
    conf["session"] = {
        "init": "1",
        "default_gas_price": "1000000000",
        "default_wallet_index": "0",
        "default_eth_rpc_endpoint": "https://kovan.infura.io"
    }
    persist()


conf.persist = persist
