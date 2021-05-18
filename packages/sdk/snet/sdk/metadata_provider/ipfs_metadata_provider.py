from snet.snet_cli.metadata.service import mpe_service_metadata_from_json

from snet.snet_cli.utils.ipfs_utils import bytesuri_to_hash, get_from_ipfs_and_checkhash

import json


class IPFSMetadataProvider(object):

    def __init__(self, ipfs_client, registry_contract):
        self.registry_contract = registry_contract
        self._ipfs_client = ipfs_client

    def fetch_org_metadata(self, org_id):
        (found, id, metadata_uri, owner, members, service_ids) = self.registry_contract.functions.getOrganizationById(
            bytes(org_id, "utf-8")).call()
        if found is not True:
            raise Exception('Organization with org ID "{}" not found '.format(org_id))

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self._ipfs_client, metadata_hash)
        org_metadata = json.loads(metadata_json)
        return org_metadata

    def fetch_service_metadata(self, org_id, service_id):
        (found, registration_id, metadata_uri) = self.registry_contract.functions.getServiceRegistrationById(
            bytes(org_id, "utf-8"), bytes(service_id, "utf-8")).call()

        if found is not True:
            raise Exception('No service "{}" found in organization "{}"'.format(service_id, org_id))

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self._ipfs_client, metadata_hash)
        metadata = mpe_service_metadata_from_json(metadata_json)
        return metadata

    def enhance_service_metadata(self, org_id, service_id):
        service_metadata = self.fetch_service_metadata(org_id, service_id)
        org_metadata = self.fetch_org_metadata(org_id)

        org_group_map = {}
        for group in org_metadata['groups']:
            org_group_map[group['group_name']] = group

        for group in service_metadata.m['groups']:
            # merge service group with org_group
            group['payment'] = org_group_map[group['group_name']]['payment']

        return service_metadata
