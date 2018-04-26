from configparser import NoOptionError

from snet_cli.utils import DefaultAttributeObject


class Session(DefaultAttributeObject):
    pass


class SessionIdentity(DefaultAttributeObject):
    pass


def from_config(config):
    try:
        identity = SessionIdentity(
            eth_rpc_endpoint=config.get("identity.{}".format(config.get("session", "identity_name")),
                                        "eth_rpc_endpoint", fallback=None),
            mnemonic=config.get("identity.{}".format(config.get("session", "identity_name")),
                                "mnemonic", fallback=None),
            private_key=config.get("identity.{}".format(config.get("session", "identity_name")),
                                   "private_key", fallback=None),
            identity_type=config.get("identity.{}".format(config.get("session", "identity_name")), "identity_type"),
        )
    except NoOptionError:
        identity = None
    return Session(
        identity=identity,
        default_agent_at=config.get("session", "default_agent_at", fallback=None),
        default_agent_factory_at=config.get("session", "default_agent_factory_at", fallback=None),
        default_gas_price=config.get("session", "default_gas_price", fallback=None),
        default_eth_rpc_endpoint=config.get("session", "default_eth_rpc_endpoint", fallback=None),
        default_wallet_index=config.get("session", "default_wallet_index", fallback=None),
        default_job_at=config.get("session", "default_job_at", fallback=None),
        default_registry_at=config.get("session", "default_registry_at", fallback=None),
        default_singularity_net_token_at=config.get("session", "default_singularity_net_token_at", fallback=None)
    )


def get_session_keys():
    return ["default_agent_at", "default_agent_factory_at", "default_gas_price", "default_eth_rpc_endpoint",
            "default_wallet_index", "default_job_at", "default_registry_at", "identity_name"]
