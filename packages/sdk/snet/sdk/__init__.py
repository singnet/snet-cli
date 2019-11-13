import google.protobuf.internal.api_implementation

from packages.sdk.snet.sdk.metadata_provider.ipfs_metadata_provider import IPFSMetadataProvider

google.protobuf.internal.api_implementation.Type = lambda: 'python'

from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
_sym_db.RegisterMessage = lambda x: None


import sys

import json
import base64
from urllib.parse import urljoin
from pathlib import Path, PurePath

import web3
from web3.gas_strategies.time_based import medium_gas_price_strategy
from rfc3986 import urlparse
import ipfsapi
from web3.datastructures import AttributeDict

from snet.sdk.service_client import ServiceClient
from snet.sdk.dynamic_service_client import DynamicServiceClient
from snet.sdk.account import Account
from snet.sdk.mpe_contract import MPEContract
from snet.sdk.payment_channel_management_strategies.default import PaymentChannelManagementStrategy

from snet.snet_cli.utils import get_contract_object, compile_proto
from snet.snet_cli.utils_proto import import_protobuf_from_dir
from snet.snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash, safe_extract_proto_from_ipfs
from snet.snet_cli.mpe_service_metadata import mpe_service_metadata_from_json

class SnetSDK:
    """Base Snet SDK"""

    def __init__(
        self,
        config, metadata_provider=None
    ):
        self._config = config
        self._metadata_provider = metadata_provider

        # Instantiate Ethereum client
        eth_rpc_endpoint = self._config.get("eth_rpc_endpoint", "https://mainnet.infura.io")
        provider = web3.HTTPProvider(eth_rpc_endpoint)
        self.web3 = web3.Web3(provider)
        self.web3.eth.setGasPriceStrategy(medium_gas_price_strategy)

        # Get MPE contract address from config if specified; mostly for local testing
        _mpe_contract_address = self._config.get("mpe_contract_address", None)
        if _mpe_contract_address is None:
            self.mpe_contract = MPEContract(self.web3)
        else:
            self.mpe_contract = MPEContract(self.web3, _mpe_contract_address)

        # Instantiate IPFS client
        ipfs_rpc_endpoint = self._config.get("ipfs_rpc_endpoint", "https://ipfs.singularitynet.io:80")
        ipfs_rpc_endpoint = urlparse(ipfs_rpc_endpoint)
        ipfs_scheme = ipfs_rpc_endpoint.scheme if ipfs_rpc_endpoint.scheme else "http"
        ipfs_port = ipfs_rpc_endpoint.port if ipfs_rpc_endpoint.port else 5001
        self.ipfs_client = ipfsapi.connect(urljoin(ipfs_scheme, ipfs_rpc_endpoint.hostname), ipfs_port)

        # Get Registry contract address from config if specified; mostly for local testing
        _registry_contract_address = self._config.get("registry_contract_address", None)
        if _registry_contract_address is None:
            self.registry_contract = get_contract_object(self.web3, "Registry.json")
        else:
            self.registry_contract = get_contract_object(self.web3, "Registry.json", _registry_contract_address)

        self.account = Account(self.web3, config, self.mpe_contract)

    def create_service_client(self, org_id, service_id, service_stub, group_name,
                              payment_channel_management_strategy=PaymentChannelManagementStrategy, options=None):
        if options is None:
            options = dict()

        if self._metadata_provider is None:
            self._metadata_provider = IPFSMetadataProvider( self.ipfs_client ,self.web3)

        service_metadata = self._metadata_provider.enhance_service_metadata(org_id, service_id)
        group = self.get_service_group_details(service_metadata, group_name)
        strategy = payment_channel_management_strategy(self)
        service_client = ServiceClient(self, service_metadata, group, service_stub, strategy, options )
        return service_client

    def create_dynamic_service_client(self, org_id, service_id, group_name=None, payment_channel_management_strategy=PaymentChannelManagementStrategy, options=None):
        if options is None:
            options = dict()

        service_metadata = self.get_service_metadata(org_id, service_id)
        group = service_metadata.get_group(group_name)
        strategy = payment_channel_management_strategy(self)
        grpc_output_path = PurePath(Path.resolve(Path(sys.argv[0]))).parent.joinpath("grpc", org_id, service_id)
        dynamic_service_client = DynamicServiceClient(self, service_metadata, group, org_id, service_id, grpc_output_path, strategy, options)
        return dynamic_service_client


    def get_service_metadata(self, org_id, service_id):
        (found, registration_id, metadata_uri, tags) = self.registry_contract.functions.getServiceRegistrationById(bytes(org_id, "utf-8"), bytes(service_id, "utf-8")).call()

        if found is not True:
            raise Exception('No service "{}" found in organization "{}"'.format(service_id, org_id))

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self.ipfs_client, metadata_hash)
        metadata = mpe_service_metadata_from_json(metadata_json)
        return metadata

    def get_service_group_details(self, service_metadata,group_name):
        for group in service_metadata['groups']:
            if group['group_name'] == group_name:
                return group

