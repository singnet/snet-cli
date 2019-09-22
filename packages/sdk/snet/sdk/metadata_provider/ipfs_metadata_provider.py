from urllib.parse import urljoin

from rfc3986 import urlparse
from snet.snet_cli.mpe_orgainzation_metadata import OrganizationMetadata

from snet.snet_cli.mpe_service_metadata import mpe_service_metadata_from_json
from snet.snet_cli.utils import (
    type_converter,
    safe_address_converter,
    get_contract_object,
)

from snet.snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash
import web3
import json
import ipfsapi


class IPFSMetadataProvider(object):
    def __init__(self, ipfs_client, web3):
        self._web3 = web3
        self.registry_contract = get_contract_object(self._web3, "Registry.json")
        self._ipfs_client = ipfs_client

    def fetch_org_metadata(self, org_id):
        (
            found,
            id,
            metadata_uri,
            owner,
            members,
            serviceIds,
            repositoryIds,
        ) = self.registry_contract.functions.getOrganizationById(
            bytes(org_id, "utf-8")
        ).call()
        print("dd")
        if found is not True:
            raise Exception('No  organization is foubd "{}"'.format(org_id))

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self._ipfs_client, metadata_hash)
        org_metadata = json.loads(metadata_json)
        return org_metadata

    def fetch_service_metadata(self, org_id, service_id):
        (
            found,
            registration_id,
            metadata_uri,
            tags,
        ) = self.registry_contract.functions.getServiceRegistrationById(
            bytes(org_id, "utf-8"), bytes(service_id, "utf-8")
        ).call()

        if found is not True:
            raise Exception(
                'No service "{}" found in organization "{}"'.format(service_id, org_id)
            )

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self._ipfs_client, metadata_hash)
        metadata = mpe_service_metadata_from_json(metadata_json)
        return metadata

    def enhance_service_metadata(self, org_id, service_id):
        service_metadata = self.fetch_service_metadata(org_id, service_id)
        org_metadata = self.fetch_org_metadata(org_id)

        org_group_map = {}
        for group in org_metadata["groups"]:
            org_group_map[group["group_name"]] = group

        for group in service_metadata.m["groups"]:
            # merge service group with org_group
            group["payment"] = org_group_map[group["group_name"]]["payment"]

        return service_metadata


# need to delete this once contract is finalized
if __name__ == "__main__":

    def _get_ipfs_client():
        # Instantiate IPFS client
        ipfs_rpc_endpoint = "https://ipfs.singularitynet.io:80"
        ipfs_rpc_endpoint = urlparse(ipfs_rpc_endpoint)
        ipfs_scheme = ipfs_rpc_endpoint.scheme if ipfs_rpc_endpoint.scheme else "http"
        ipfs_port = ipfs_rpc_endpoint.port if ipfs_rpc_endpoint.port else 5001
        return ipfsapi.connect(
            urljoin(ipfs_scheme, ipfs_rpc_endpoint.hostname), ipfs_port
        )

    eth_rpc_endpoint = "https://ropsten.infura.io/v3/e7732e1f679e461b9bb4da5653ac3fc2"
    provider = web3.HTTPProvider(eth_rpc_endpoint)
    web3 = web3.Web3(provider)
    ip = IPFSMetadataProvider(_get_ipfs_client(), web3)
    s_m = ip.enhance_service_metadata("nginx_snet", "nginx_snet")
    print("345")
    # ip.fetch_org_metadata('nginx_snet')
    pass
