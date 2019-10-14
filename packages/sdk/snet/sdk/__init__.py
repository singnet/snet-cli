import base64
import json
from urllib.parse import urljoin

import google.protobuf.internal.api_implementation
import ipfsapi
import web3
from google.protobuf import symbol_database as _symbol_database
from rfc3986 import urlparse
from snet.sdk.account import Account
from snet.sdk.mpe_contract import MPEContract
from snet.sdk.payment_channel_management_strategies.default import (
    PaymentChannelManagementStrategy,
)
from snet.sdk.service_client import ServiceClient
from snet.snet_cli.mpe_service_metadata import mpe_service_metadata_from_json
from snet.snet_cli.utils import get_contract_object
from snet.snet_cli.utils_ipfs import bytesuri_to_hash
from snet.snet_cli.utils_ipfs import get_from_ipfs_and_checkhash
from web3.datastructures import AttributeDict
from web3.gas_strategies.time_based import medium_gas_price_strategy

from packages.sdk.snet.sdk.metadata_provider.ipfs_metadata_provider import (
    IPFSMetadataProvider,
)

google.protobuf.internal.api_implementation.Type = lambda: "python"


_sym_db = _symbol_database.Default()
_sym_db.RegisterMessage = lambda x: None


class SnetSDK:
    """Base Snet SDK"""

    def __init__(self, config, metadata_provider=None):
        self._config = config
        self._metadata_provider = metadata_provider

        # Instantiate Ethereum client
        eth_rpc_endpoint = self._config.get(
            "eth_rpc_endpoint", "https://mainnet.infura.io"
        )
        provider = web3.HTTPProvider(eth_rpc_endpoint)
        self.web3 = web3.Web3(provider)
        self.web3.eth.setGasPriceStrategy(medium_gas_price_strategy)

        self.mpe_contract = MPEContract(self.web3)

        # Instantiate IPFS client
        ipfs_rpc_endpoint = self._config.get(
            "ipfs_rpc_endpoint", "https://ipfs.singularitynet.io:80"
        )
        ipfs_rpc_endpoint = urlparse(ipfs_rpc_endpoint)
        ipfs_scheme = ipfs_rpc_endpoint.scheme if ipfs_rpc_endpoint.scheme else "http"
        ipfs_port = ipfs_rpc_endpoint.port if ipfs_rpc_endpoint.port else 5001
        self.ipfs_client = ipfsapi.connect(
            urljoin(ipfs_scheme, ipfs_rpc_endpoint.hostname), ipfs_port
        )

        self.registry_contract = get_contract_object(self.web3, "Registry.json")
        self.account = Account(self.web3, config, self.mpe_contract)

    def create_service_client(
        self,
        org_id,
        service_id,
        service_stub,
        group_name,
        payment_channel_management_strategy=PaymentChannelManagementStrategy,
        options=None,
    ):
        if options is None:
            options = dict()

        if self._metadata_provider is None:
            self._metadata_provider = IPFSMetadataProvider(self.ipfs_client, self.web3)

        service_metadata = self._metadata_provider.enhance_service_metadata(
            org_id, service_id
        )
        group = self.get_service_group_details(service_metadata, group_name)
        strategy = payment_channel_management_strategy(self)
        service_client = ServiceClient(
            self, service_metadata, group, service_stub, strategy, options
        )
        return service_client

    def get_service_group_details(self, service_metadata, group_name):
        for group in service_metadata["groups"]:
            if group["group_name"] == group_name:
                return group
