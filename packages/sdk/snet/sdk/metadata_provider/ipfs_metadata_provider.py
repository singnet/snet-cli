from snet.snet_cli.mpe_service_metadata import mpe_service_metadata_from_json
from snet.snet_cli.utils import type_converter, safe_address_converter

from snet.snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash
import web3
import json


class IPFSMetadataProvider(object):

    def __init__(self, ipfs_endpoint, network_id, web3):
        pass

    def safe_address_converter(a):
        if not web3.eth.is_checksum_address(a):
            raise Exception("%s is not is not a valid Ethereum checksum address" % a)
        return a

    def type_converter(t):
        if t.endswith("[]"):
            return lambda x: list(map(type_converter(t.replace("[]", "")), json.loads(x)))
        else:
            if "int" in t:
                return lambda x: web3.Web3.toInt(text=x)
            elif "bytes32" in t:
                return lambda x: web3.Web3.toBytes(text=x).ljust(32, b"\0") if not x.startswith(
                    "0x") else web3.Web3.toBytes(hexstr=x).ljust(32, b"\0")
            elif "byte" in t:
                return lambda x: web3.Web3.toBytes(text=x) if not x.startswith("0x") else web3.Web3.toBytes(hexstr=x)
            elif "address" in t:
                return safe_address_converter
            else:
                return str

    def bytes32_to_str(b):
        return b.rstrip(b"\0").decode("utf-8")

    def _get_organization_metadata_from_registry(self, org_id):
        rez = self._get_organization_registration(org_id)
        metadata_hash = bytesuri_to_hash(rez["orgMetadataURI"])
        metadata = get_from_ipfs_and_checkhash(
            self._get_ipfs_client(), metadata_hash)
        metadata = metadata.decode("utf-8")
        return json.loads(metadata)

    def _get_organization_registration(self, org_id):
        params = [type_converter("bytes32")(org_id)]
        rez = self.call_contract_command(
            "Registry", "getOrganizationById", params)
        if (rez[0] == False):
            raise Exception("Cannot find  Organization with id=%s" % (
                self.args.org_id))
        return {"orgMetadataURI": rez[2]}

    def get_org_metadata(self, org_id):
        return self.__get_organization_metadata_from_registry(org_id)

    def fetch_org_metadata(self, org_id):
        return self._get_organization_metadata_from_registry(org_id)

    def fetch_service_metadata(self, org_id, service_id):
        (found, registration_id, metadata_uri, tags) = self.registry_contract.functions.getServiceRegistrationById(
            bytes(org_id, "utf-8"), bytes(service_id, "utf-8")).call()

        if found is not True:
            raise Exception('No service "{}" found in organization "{}"'.format(service_id, org_id))

        metadata_hash = bytesuri_to_hash(metadata_uri)
        metadata_json = get_from_ipfs_and_checkhash(self.ipfs_client, metadata_hash)
        metadata = mpe_service_metadata_from_json(metadata_json)
        return metadata

    def enhance_service_metadata(self, org_id, service_id):
        service_metadata = self.fetch_service_metadata(org_id, service_id)
        org_metadata = self.fetch_org_metadata(org_id)
