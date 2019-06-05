import json
import base64
from urllib.parse import urljoin

import web3
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from rfc3986 import urlparse
import ipfsapi
from web3.utils.datastructures import AttributeDict

from snet_sdk.utils import get_contract_object
from snet_sdk.service_client import ServiceClient
from snet_sdk.account import Account
from snet_sdk.mpe_contract import MPEContract
from snet_sdk.payment_channel_management_strategies.default import PaymentChannelManagementStrategy


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
        self.web3.eth.setGasPriceStrategy(rpc_gas_price_strategy)

        self.mpe_contract = MPEContract(self.web3)

        # Instantiate IPFS client
        ipfs_rpc_endpoint = self._config.get("ipfs_rpc_endpoint", "https://ipfs.singularitynet.io:80")
        ipfs_rpc_endpoint = urlparse(ipfs_rpc_endpoint)
        ipfs_scheme = ipfs_rpc_endpoint.scheme if ipfs_rpc_endpoint.scheme else "http"
        ipfs_port = ipfs_rpc_endpoint.port if ipfs_rpc_endpoint.port else 5001
        self.ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_rpc_endpoint.hostname), ipfs_port)

        self.registry_contract = get_contract_object(self.web3, "Registry.json")
        self.account = Account(self.web3, config, self.mpe_contract)


    def create_service_client(self, org_id, service_id, service_stub, group_name="default_group", payment_channel_management_strategy=PaymentChannelManagementStrategy, options={}):
        service_metadata = self.service_metadata(org_id, service_id)
        try:
            group = next(filter(lambda group: group["group_name"] == group_name, service_metadata.groups))
        except StopIteration:
            raise ValueError("Group[name: {}] not found for orgId: {} and serviceId: {}".format(group_name, org_id, service_id))
        service_client = ServiceClient(self, service_metadata, group, service_stub, payment_channel_management_strategy(self), options)
        return service_client

    def service_metadata(self, org_id, service_id):
        (found, registration_id, metadata_uri, tags) = self.registry_contract.functions.getServiceRegistrationById(bytes(org_id, "utf-8"), bytes(service_id, "utf-8")).call()
        metadata = AttributeDict(json.loads(self.ipfs_client.cat(metadata_uri.rstrip(b"\0").decode('ascii')[7:])))
        return metadata
