import json
import base64
from urllib.parse import urljoin

import web3
from web3.gas_strategies.time_based import medium_gas_price_strategy
from rfc3986 import urlparse
import ipfsapi
from web3.datastructures import AttributeDict

from snet.sdk.service_client import ServiceClient
from snet.sdk.account import Account
from snet.sdk.mpe_contract import MPEContract
from snet.sdk.payment_channel_management_strategies.default import PaymentChannelManagementStrategy

from snet.snet_cli.utils import get_contract_object
from snet.snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash
from snet.snet_cli.mpe_service_metadata import mpe_service_metadata_from_json


class SnetSDK:
    """Base Snet SDK"""
    def __init__(
        self,
        config
    ):
        self._config = config

        # Instantiate Ethereum client
        eth_rpc_endpoint = self._config.get("eth_rpc_endpoint", "https://mainnet.infura.io")
        provider = web3.HTTPProvider(eth_rpc_endpoint)
        self.web3 = web3.Web3(provider)
        self.web3.eth.setGasPriceStrategy(medium_gas_price_strategy)

        self.mpe_contract = MPEContract(self.web3)

        # Instantiate IPFS client
        ipfs_rpc_endpoint = self._config.get("ipfs_rpc_endpoint", "https://ipfs.singularitynet.io:80")
        ipfs_rpc_endpoint = urlparse(ipfs_rpc_endpoint)
        ipfs_scheme = ipfs_rpc_endpoint.scheme if ipfs_rpc_endpoint.scheme else "http"
        ipfs_port = ipfs_rpc_endpoint.port if ipfs_rpc_endpoint.port else 5001
        self.ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_rpc_endpoint.hostname), ipfs_port)

        self.registry_contract = get_contract_object(self.web3, "Registry.json")
        self.account = Account(self.web3, config, self.mpe_contract)


    def create_service_client(self, org_id, service_id, service_stub, group_name=None, payment_channel_management_strategy=PaymentChannelManagementStrategy, options=None):
        if options is None:
            options = dict()

        service_metadata = self.get_service_metadata(org_id, service_id)
        group = service_metadata.get_group(group_name)
        strategy = payment_channel_management_strategy(self)
        service_client = ServiceClient(self, service_metadata, group, service_stub, strategy, options)
        return service_client


    def get_service_metadata(self, org_id, service_id):
        (found, registration_id, metadata_uri, tags) = self.registry_contract.functions.getServiceRegistrationById(bytes(org_id, "utf-8"), bytes(service_id, "utf-8")).call()
        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self.ipfs_client, metadata_hash)
        metadata = mpe_service_metadata_from_json(metadata_json)
        return metadata
