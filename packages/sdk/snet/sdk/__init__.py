import google.protobuf.internal.api_implementation
from snet.sdk.metadata_provider.ipfs_metadata_provider import IPFSMetadataProvider
from snet.sdk.payment_strategies.default_payment_strategy import DefaultPaymentStrategy

google.protobuf.internal.api_implementation.Type = lambda: 'python'

from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
_sym_db.RegisterMessage = lambda x: None


from urllib.parse import urljoin


import web3
from web3.gas_strategies.time_based import medium_gas_price_strategy
from rfc3986 import urlparse
import ipfsapi

from snet.sdk.service_client import ServiceClient
from snet.sdk.account import Account
from snet.sdk.mpe.mpe_contract import MPEContract

from snet.snet_cli.utils.utils import get_contract_object

from snet.snet_cli.utils.ipfs_utils import bytesuri_to_hash, get_from_ipfs_and_checkhash
from snet.snet_cli.metadata.service import mpe_service_metadata_from_json

class SnetSDK:
    """Base Snet SDK"""

    def __init__(
        self,
        config, metadata_provider=None
    ):
        self._config = config
        self._metadata_provider = metadata_provider

        # Instantiate Ethereum client
        eth_rpc_endpoint = self._config.get("eth_rpc_endpoint", "https://mainnet.infura.io/v3/e7732e1f679e461b9bb4da5653ac3fc2")
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

    def create_service_client(self, org_id, service_id, service_stub, group_name=None,
                              payment_channel_management_strategy=None, options=None, concurrent_calls=1):
        if payment_channel_management_strategy is None:
            payment_channel_management_strategy = DefaultPaymentStrategy(concurrent_calls)
        if options is None:
            options = dict()

        options['free_call_auth_token-bin'] = bytes.fromhex(self._config.get("free_call_auth_token-bin", ""))
        options['free-call-token-expiry-block'] = self._config.get("free-call-token-expiry-block", 0)
        options['email'] = self._config.get("email", "")
        options['concurrency'] = self._config.get("concurrency", True)

        if self._metadata_provider is None:
            self._metadata_provider = IPFSMetadataProvider( self.ipfs_client ,self.registry_contract,)

        service_metadata = self._metadata_provider.enhance_service_metadata(org_id, service_id)
        group = self._get_service_group_details(service_metadata, group_name)
        strategy = payment_channel_management_strategy
        service_client = ServiceClient(org_id, service_id, service_metadata, group, service_stub, strategy, options,
                                       self.mpe_contract, self.account, self.web3)
        return service_client


    def get_service_metadata(self, org_id, service_id):
        (found, registration_id, metadata_uri) = self.registry_contract.functions.getServiceRegistrationById(bytes(org_id, "utf-8"), bytes(service_id, "utf-8")).call()

        if found is not True:
            raise Exception('No service "{}" found in organization "{}"'.format(service_id, org_id))

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self.ipfs_client, metadata_hash)
        metadata = mpe_service_metadata_from_json(metadata_json)
        return metadata

    def _get_first_group(self, service_metadata):
        return service_metadata['groups'][0]

    def _get_group_by_group_name(self, service_metadata, group_name):
        for group in service_metadata['groups']:
            if group['group_name'] == group_name:
                return group
        return {}

    def _get_service_group_details(self, service_metadata, group_name):
        if len(service_metadata['groups']) == 0:
            raise Exception("No Groups found for geivne service,Please add group to the service")

        if group_name is None:
            return self._get_first_group(service_metadata)

        return self._get_group_by_group_name(service_metadata, group_name)
