import json
from collections import defaultdict

import snet.snet_cli.utils.ipfs_utils as ipfs_utils
from grpc_health.v1 import health_pb2 as heartb_pb2
from grpc_health.v1 import health_pb2_grpc as heartb_pb2_grpc
from snet.snet_cli.metadata.service import MPEServiceMetadata, load_mpe_service_metadata, \
    mpe_service_metadata_from_json
from snet.snet_cli.metadata.organization import OrganizationMetadata
from snet.snet_cli.utils.ipfs_utils import hash_to_bytesuri, bytesuri_to_hash, get_from_ipfs_and_checkhash, \
    safe_extract_proto_from_ipfs
from snet.snet_cli.utils.utils import type_converter, bytes32_to_str, open_grpc_channel
from snet_cli.commands.commands import BlockchainCommand


class MPEServiceCommand(BlockchainCommand):

    def publish_proto_in_ipfs(self):
        """ Publish proto files in ipfs and print hash """
        ipfs_hash_base58 = ipfs_utils.publish_proto_in_ipfs(
            self._get_ipfs_client(), self.args.protodir)
        self._printout(ipfs_hash_base58)

    def publish_proto_metadata_init(self):
        model_ipfs_hash_base58 = ipfs_utils.publish_proto_in_ipfs(
            self._get_ipfs_client(), self.args.protodir)

        metadata = MPEServiceMetadata()
        mpe_address = self.get_mpe_address()
        metadata.set_simple_field("model_ipfs_hash",
                                  model_ipfs_hash_base58)
        metadata.set_simple_field("mpe_address", mpe_address)
        metadata.set_simple_field("display_name",
                                  self.args.display_name)
        metadata.set_simple_field("encoding",
                                  self.args.encoding)
        metadata.set_simple_field("service_type",
                                  self.args.service_type)

        if self.args.group_name:
            metadata.add_group(self.args.group_name)
            if self.args.endpoints:
                for endpoint in self.args.endpoints:
                    metadata.add_endpoint_to_group(
                        self.args.group_name, endpoint)
            if self.args.fixed_price is not None:
                metadata.set_fixed_price_in_cogs(
                    self.args.group_name, self.args.fixed_price)
        elif self.args.group_name or self.args.fixed_price:
            raise Exception(
                "endpoints / fixed price can be attached to a group please pass group_name")
        metadata.save_pretty(self.args.metadata_file)

    def publish_proto_metadata_update(self):
        """ Publish protobuf model in ipfs and update existing metadata file """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        ipfs_hash_base58 = ipfs_utils.publish_proto_in_ipfs(
            self._get_ipfs_client(), self.args.protodir)
        metadata.set_simple_field("model_ipfs_hash", ipfs_hash_base58)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_set_fixed_price(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.set_fixed_price_in_cogs(self.args.group_name, self.args.price)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_set_method_price(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.set_method_price_in_cogs(
            self.args.group_name, self.args.package_name, self.args.service_name, self.args.method, self.args.price)
        metadata.save_pretty(self.args.metadata_file)

    def _metadata_add_group(self, metadata):
        metadata.add_group(self.args.group_name)

    def metadata_add_group(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        self._metadata_add_group(metadata)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_group(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_group(self.args.group_name)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_set_free_calls(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.set_free_calls_for_group(self.args.group_name, int(self.args.free_calls))
        metadata.save_pretty(self.args.metadata_file)

    def metadata_set_freecall_signer_address(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.set_freecall_signer_address(self.args.group_name, self.args.signer_address)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_add_daemon_addresses(self):
        """ Metadata: add daemon addresses to the group """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        group_name = metadata.get_group_name_nonetrick(self.args.group_name)
        for daemon_address in self.args.daemon_addresses:
            metadata.add_daemon_address_to_group(group_name, daemon_address)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_all_daemon_addresses(self):
        """ Metadata: remove all daemon addresses from all groups """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_all_daemon_addresses_for_group(self.args.group_name)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_update_daemon_addresses(self):
        """ Metadata: Remove all daemon addresses from the group and add new ones """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        group_name = metadata.get_group_name_nonetrick(self.args.group_name)
        metadata.remove_all_daemon_addresses_for_group(group_name)
        for daemon_address in self.args.daemon_addresses:
            metadata.add_daemon_address_to_group(group_name, daemon_address)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_add_endpoints(self):
        """ Metadata: add endpoint to the group """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        group_name = metadata.get_group_name_nonetrick(self.args.group_name)
        for endpoint in self.args.endpoints:
            metadata.add_endpoint_to_group(group_name, endpoint)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_all_endpoints(self):
        """ Metadata: remove all endpoints from all groups """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_all_endpoints_for_group(self.args.group_name)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_update_endpoints(self):
        """ Metadata: Remove all endpoints from the group and add new ones """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        group_name = metadata.get_group_name_nonetrick(self.args.group_name)
        metadata.remove_all_endpoints_for_group(group_name)
        for endpoint in self.args.endpoints:
            metadata.add_endpoint_to_group(group_name, endpoint)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_add_asset_to_ipfs(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        asset_file_ipfs_hash_base58 = ipfs_utils.publish_file_in_ipfs(self._get_ipfs_client(),
                                                                      self.args.asset_file_path)

        metadata.add_asset(asset_file_ipfs_hash_base58, self.args.asset_type)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_all_assets(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_all_assets()
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_assets_of_a_given_type(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_assets(self.args.asset_type)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_add_contributor(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.add_contributor(self.args.name, self.args.email_id)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_contributor(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_contributor_by_email(self.args.email_id)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_add_description(self):
        """ Metadata: add description """
        service_description = {}
        if (self.args.json):
            service_description = json.loads(self.args.json)
        if (self.args.url):
            if "url" in service_description:
                raise Exception(
                    "json service description already contains url field")
            service_description["url"] = self.args.url
        if (self.args.description):
            if "description" in service_description:
                raise Exception(
                    "json service description already contains description field")
            service_description["description"] = self.args.description
        if self.args.short_description:
            if "short_description" in service_description:
                raise Exception(
                    "json service description already contains short description field")
            if len(self.args.short_description) > 180:
                raise Exception(
                    "size of short description must be less than 181 characters"
                )
            service_description["short_description"] = self.args.short_description
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        # merge with old service_description if necessary
        if ("service_description" in metadata):
            service_description = {
                **metadata["service_description"], **service_description}
        metadata.set_simple_field("service_description", service_description)
        metadata.save_pretty(self.args.metadata_file)

    def _publish_metadata_in_ipfs(self, metadata_file):
        metadata = load_mpe_service_metadata(metadata_file)
        mpe_address = self.get_mpe_address()
        if (self.args.update_mpe_address):
            metadata.set_simple_field("mpe_address", mpe_address)
            metadata.save_pretty(self.args.metadata_file)

        if (mpe_address.lower() != metadata["mpe_address"].lower()):
            raise Exception(
                "\n\nmpe_address in metadata does not correspond to the current MultiPartyEscrow contract address\n" +
                "You have two possibilities:\n" +
                "1. You can use --multipartyescrow-at to set current mpe address\n" +
                "2. You can use --update-mpe-address parameter to update mpe_address in metadata before publishing it\n")
        return self._get_ipfs_client().add_bytes(metadata.get_json().encode("utf-8"))

    def publish_metadata_in_ipfs(self):
        """ Publish metadata in ipfs and print hash """
        self._printout(self._publish_metadata_in_ipfs(self.args.metadata_file))

    def _get_converted_tags(self):
        return [type_converter("bytes32")(tag) for tag in self.args.tags]

    def _get_organization_metadata_from_registry(self, org_id):
        rez = self._get_organization_registration(org_id)
        metadata_hash = bytesuri_to_hash(rez["orgMetadataURI"])
        metadata = get_from_ipfs_and_checkhash(
            self._get_ipfs_client(), metadata_hash)
        metadata = metadata.decode("utf-8")
        return OrganizationMetadata.from_json(json.loads(metadata))

    def _get_organization_registration(self, org_id):
        params = [type_converter("bytes32")(org_id)]
        rez = self.call_contract_command(
            "Registry", "getOrganizationById", params)
        if (rez[0] == False):
            raise Exception("Cannot find  Organization with id=%s" % (
                self.args.org_id))
        return {"orgMetadataURI": rez[2]}

    def _validate_service_group_with_org_group_and_update_group_id(self, org_id, metadata_file):
        org_metadata = self._get_organization_metadata_from_registry(org_id)
        new_service_metadata = load_mpe_service_metadata(metadata_file)
        org_groups = {}
        for group in org_metadata.groups:
            org_groups[group.group_name] = group

        for group in new_service_metadata.m["groups"]:
            if group["group_name"] in org_groups:
                group["group_id"] = org_groups[group["group_name"]].group_id
                new_service_metadata.save_pretty(metadata_file)
            else:
                raise Exception(
                    "Group name %s does not exist in organization" % group["group_name"])

    def publish_service_with_metadata(self):

        self._validate_service_group_with_org_group_and_update_group_id(
            self.args.org_id, self.args.metadata_file)
        metadata_uri = hash_to_bytesuri(
            self._publish_metadata_in_ipfs(self.args.metadata_file))
        tags = self._get_converted_tags()
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id), metadata_uri, tags]
        self.transact_contract_command(
            "Registry", "createServiceRegistration", params)

    def publish_metadata_in_ipfs_and_update_registration(self):
        # first we check that we do not change payment_address or group_id in existed payment groups
        self._validate_service_group_with_org_group_and_update_group_id(
            self.args.org_id, self.args.metadata_file)
        metadata_uri = hash_to_bytesuri(
            self._publish_metadata_in_ipfs(self.args.metadata_file))
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id), metadata_uri]
        self.transact_contract_command(
            "Registry", "updateServiceRegistration", params)

    def _get_params_for_tags_update(self):
        tags = self._get_converted_tags()
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id), tags]
        return params

    def update_registration_add_tags(self):
        params = self._get_params_for_tags_update()
        self.transact_contract_command(
            "Registry", "addTagsToServiceRegistration", params)

    def update_registration_remove_tags(self):
        params = self._get_params_for_tags_update()
        self.transact_contract_command(
            "Registry", "removeTagsFromServiceRegistration", params)

    def _get_service_registration(self):
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id)]
        rez = self.call_contract_command(
            "Registry", "getServiceRegistrationById", params)
        if (rez[0] == False):
            raise Exception("Cannot find Service with id=%s in Organization with id=%s" % (
                self.args.service_id, self.args.org_id))
        return {"metadataURI": rez[2], "tags": rez[3]}

    def _get_service_metadata_from_registry(self):
        rez = self._get_service_registration()
        metadata_hash = bytesuri_to_hash(rez["metadataURI"])
        metadata = get_from_ipfs_and_checkhash(
            self._get_ipfs_client(), metadata_hash)
        metadata = metadata.decode("utf-8")
        metadata = mpe_service_metadata_from_json(metadata)
        return metadata

    def print_service_metadata_from_registry(self):
        metadata = self._get_service_metadata_from_registry()
        self._printout(metadata.get_json_pretty())

    def _service_status(self, url, secure=True):
        try:
            channel = open_grpc_channel(endpoint=url)
            stub = heartb_pb2_grpc.HealthStub(channel)
            response = stub.Check(
                heartb_pb2.HealthCheckRequest(service=""), timeout=10)
            if response != None and response.status == 1:
                return True
            return False
        except Exception as e:
            return False

    def print_service_status(self):
        metadata = self._get_service_metadata_from_registry()
        groups = []
        if self.args.group_name != None:
            groups = {self.args.group_name: metadata.get_all_endpoints_for_group(
                self.args.group_name)}
        else:
            groups = metadata.get_all_group_endpoints()
        srvc_status = defaultdict(list)
        for name, group_endpoints in groups.items():
            for endpoint in group_endpoints:
                status = "Available" if self._service_status(
                    url=endpoint) else "Not Available"
                srvc_status[name].append(
                    {"endpoint": endpoint, "status": status})
        if srvc_status == {}:
            self._printout(
                "Error: No endpoints found to check service status.")
            return
        self._pprint(srvc_status)

    def print_service_tags_from_registry(self):
        rez = self._get_service_registration()
        tags = rez["tags"]
        tags = [bytes32_to_str(tag) for tag in tags]
        self._printout(" ".join(tags))

    def extract_service_api_from_metadata(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        safe_extract_proto_from_ipfs(self._get_ipfs_client(
        ), metadata["model_ipfs_hash"], self.args.protodir)

    def extract_service_api_from_registry(self):
        metadata = self._get_service_metadata_from_registry()
        safe_extract_proto_from_ipfs(self._get_ipfs_client(
        ), metadata["model_ipfs_hash"], self.args.protodir)

    def delete_service_registration(self):
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id)]
        self.transact_contract_command(
            "Registry", "deleteServiceRegistration", params)
