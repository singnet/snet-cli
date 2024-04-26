import json
from collections import defaultdict
from pathlib import Path
from re import search
from sys import exit

from grpc_health.v1 import health_pb2 as heartb_pb2
from grpc_health.v1 import health_pb2_grpc as heartb_pb2_grpc
from jsonschema import validate, ValidationError

from snet.cli.commands.commands import BlockchainCommand
from snet.cli.metadata.organization import OrganizationMetadata
from snet.cli.metadata.service import MPEServiceMetadata, load_mpe_service_metadata, mpe_service_metadata_from_json
from snet.cli.utils import ipfs_utils
from snet.cli.utils.utils import open_grpc_channel, type_converter


class MPEServiceCommand(BlockchainCommand):

    def publish_proto_in_ipfs(self):
        """ Publish proto files in ipfs and print hash """
        ipfs_hash_base58 = ipfs_utils.publish_proto_in_ipfs(
            self._get_ipfs_client(), self.args.protodir)
        self._printout(ipfs_hash_base58)

    def service_metadata_init(self):
        """Utility for creating a service metadata file.

        CLI questionnaire for service metadata creation. Creates a `service_metadata.json`
        (if file name is not set) with values entered by the user in the questionnaire utility.

        Mandatory args:
            display_name: Display name of the service.
            org_id: Organization ID the service would be assosciated with.
            protodir_path: Directory containing protobuf files.
            groups: Payment groups supported by the organization (default: `default_group`). If multiple
                payment groups, ask user for entry.
            endpoints: Storage end points for the clients to connect.
            daemon_addresses: Ethereum public addresses of daemon in given payment group of service.

        Optional args:
            url: Service user guide resource.
            long_description: Long description of service.
            short_description: Service overview.
            contributors: Contributor name and email-id.
            file_name: Service metdadata filename.
        """
        print("This utility will walk you through creating the service metadata file.",
             "It only covers the most common items and tries to guess sensible defaults.",
             "",
             "See `snet service metadata-init-utility -h` on how to use this utility.",
             "",
             "Press ^C at any time to quit.", sep='\n')
        try:
            metadata = MPEServiceMetadata()
            while True:
                display_name = input("display name: ").strip()
                if display_name == "":
                    print("display name is required.")
                else:
                    break
            # Find number of payment groups available for organization
            # If only 1, set `default_group` as payment group
            while True:
                org_id = input(f"organization id `{display_name}` service would be linked to: ").strip()
                while org_id == "":
                    org_id = input(f"organization id required: ").strip()
                try:
                    org_metadata = self._get_organization_metadata_from_registry(org_id)
                    no_of_groups = len(org_metadata.groups)
                    break
                except Exception:
                    print(f"`{org_id}` is invalid.")
            while True:
                try:
                    protodir_path = input("protodir path: ")
                    model_ipfs_hash_base58 = ipfs_utils.publish_proto_in_ipfs(self._get_ipfs_client(), protodir_path)
                    break
                except Exception:
                    print(f'Invalid path: "{protodir_path}"')
            if no_of_groups == 1:
                metadata.group_init('default_group')
            else:
                while input("Add group? [y/n] ") == 'y':
                    metadata.group_init(input('group name: '))
            metadata.add_description()
            metadata.add_contributor(input('Enter contributor name: '), input('Enter contributor email: '))
            while input('Add another contributor? [y/n] ').lower() == 'y':
                metadata.add_contributor(input('Enter contributor name '), input('Enter contributor email: '))
            mpe_address = self.get_mpe_address()

            metadata.set_simple_field('model_ipfs_hash', model_ipfs_hash_base58)
            metadata.set_simple_field('mpe_address', mpe_address)
            metadata.set_simple_field('display_name', display_name)
            print('', '', json.dumps(metadata.m, indent=2), sep='\n')
            print("Are you sure you want to create? [y/n] ", end='')
            if input() == 'y':
                file_name = input(f"Choose file name: (service_metadata) ") or 'service_metadata'
                file_name += '.json'
                metadata.save_pretty(file_name)
                print(f"{file_name} created.")
            else:
                exit("ABORTED.")
        except KeyboardInterrupt:
            exit("\n`snet service metadata-init-utility` CANCELLED.")

    def publish_proto_metadata_init(self):
        model_ipfs_hash_base58 = ipfs_utils.publish_proto_in_ipfs(
            self._get_ipfs_client(), self.args.protodir)

        metadata = MPEServiceMetadata()
        mpe_address = self.get_mpe_address()
        metadata.set_simple_field("model_ipfs_hash", model_ipfs_hash_base58)
        metadata.set_simple_field("mpe_address", mpe_address)
        metadata.set_simple_field("display_name", self.args.display_name)
        metadata.set_simple_field("encoding", self.args.encoding)
        metadata.set_simple_field("service_type", self.args.service_type)

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

    def metadata_add_media(self):
        """Metadata: Add new individual media

        Detects media type for files to be added on IPFS, explict declaration for external resources.
        """
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        # Support endpoints only with SSL Certificate
        url_validator = r'https?:\/\/(www\.)?([-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
        # Automatic media type identification
        if search(r'^.+\.(jpg|jpeg|png|gif)$', self.args.media_url):
            media_type = 'image'
        elif search(r'^.+\.(mp4)$', self.args.media_url):
            media_type = 'video'
        elif search(url_validator, self.args.media_url):
            while True:
                try:
                    media_type = input(f"Enter the media type (image, video) present at {self.args.media_url}: ")
                except ValueError:
                    print("Choose only between (image, video).")
                else:
                    if media_type not in ('image', 'video'):
                        print("Choose only between (image, video).")
                    else:
                        break
        else:
            if search(r'(https:\/\/)?(www\.)+([-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&//=]*)', self.args.media_url):
                raise ValueError("Media endpoint supported only for secure sites.")
            else:
                raise ValueError(f"Entered url '{self.args.media_url}' is invalid.")
        file_extension_validator = r'^.+\.(jpg|jpeg|JPG|png|gif|GIF|mp4)$'
        # Detect whether to add asset on IPFS or if external resource
        if search(file_extension_validator, self.args.media_url):
            asset_file_ipfs_hash_base58 = ipfs_utils.publish_file_in_ipfs(self._get_ipfs_client(), self.args.media_url)
            metadata.add_media(asset_file_ipfs_hash_base58, media_type, self.args.hero_image)
        else:
            metadata.add_media(self.args.media_url, media_type, self.args.hero_image)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_media(self):
        """Metadata: Remove individual media using unique order key."""
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_media(self.args.order)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_all_media(self):
        """Metadata: Remove all individual media."""
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.remove_all_media()
        metadata.save_pretty(self.args.metadata_file)

    def metadata_swap_media_order(self):
        """Metadata: Swap order of two individual media given 'from' and 'to'."""
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.swap_media_order(self.args.move_from, self.args.move_to)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_change_media_order(self):
        """Metadata: REPL to change order of all individual media."""
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.change_media_order()
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
        if self.args.json:
            service_description = json.loads(self.args.json)
        if self.args.url:
            if "url" in service_description:
                raise Exception(
                    "json service description already contains url field")
            service_description["url"] = self.args.url
        if self.args.description:
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
        if "service_description" in metadata:
            service_description = {
                **metadata["service_description"], **service_description}
        metadata.set_simple_field("service_description", service_description)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_validate(self):
        """Validates the service metadata file for structure and input consistency.

        Validates whether service metadata (`service_metadata.json` if not provided as argument) is consistent
        with the schema provided in `service_schema` present in `snet_cli/snet/snet_cli/resources.`

        Args:
            metadata_file: Option provided through the command line. (default: service_metadata.json)
            service_schema: Schema of a consistent service metadata file.

        Raises:
            ValidationError: Inconsistent service metadata structure or missing values.
                docs -> Handling ValidationErrors (https://python-jsonschema.readthedocs.io/en/stable/errors/)
        """
        # Set path to `service_schema` stored in the `resources` directory from cwd of `mpe_service.py`
        current_path = Path(__file__).parent
        relative_path = '../../snet/snet_cli/resources/service_schema'
        path_to_schema = (current_path / relative_path).resolve()
        with open(path_to_schema, 'r') as f:
            schema = json.load(f)
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        try:
            validate(instance=metadata.m, schema=schema)
        except Exception as e:
            docs = "http://snet-cli-docs.singularitynet.io/service.html"
            error_message = f"\nVisit {docs} for more information."
            if e.validator == 'required':
                raise ValidationError(e.message + error_message)
            elif e.validator == 'minLength':
                raise ValidationError(f"`{e.path[-1]}` -> cannot be empty." + error_message)
            elif e.validator == 'minItems':
                raise ValidationError(f"`{e.path[-1]}` -> minimum 1 item required." + error_message)
            elif e.validator == 'type':
                raise ValidationError(f"`{e.path[-1]}` -> {e.message}" + error_message)
            elif e.validator == 'enum':
                raise ValidationError(f"`{e.path[-1]}` -> {e.message}" + error_message)
            elif e.validator == 'additionalProperties':
                if len(e.path) != 0:
                    raise ValidationError(f"{e.message} in `{e.path[-2]}`." + error_message)
                else:
                    raise ValidationError(f"{e.message} in main object." + error_message)
        else:
            exit("OK. Ready to publish.")

    def _publish_metadata_in_ipfs(self, metadata_file):
        metadata = load_mpe_service_metadata(metadata_file)
        mpe_address = self.get_mpe_address()
        if self.args.update_mpe_address:
            metadata.set_simple_field("mpe_address", mpe_address)
            metadata.save_pretty(self.args.metadata_file)

        if mpe_address.lower() != metadata["mpe_address"].lower():
            raise Exception(
                "\n\nmpe_address in metadata does not correspond to the current MultiPartyEscrow contract address\n" +
                "You have two possibilities:\n" +
                "1. You can use --multipartyescrow-at to set current mpe address\n" +
                "2. You can use --update-mpe-address parameter to update mpe_address in metadata before publishing it\n")
        return self._get_ipfs_client().add_bytes(metadata.get_json().encode("utf-8"))

    def publish_metadata_in_ipfs(self):
        """ Publish metadata in ipfs and print hash """
        self._printout(self._publish_metadata_in_ipfs(self.args.metadata_file))

    #def _get_converted_tags(self):
    #    return [type_converter("bytes32")(tag) for tag in self.args.tags]

    def _get_organization_metadata_from_registry(self, org_id):
        rez = self._get_organization_registration(org_id)
        metadata_hash = ipfs_utils.bytesuri_to_hash(rez["orgMetadataURI"])
        metadata = ipfs_utils.get_from_ipfs_and_checkhash(
            self._get_ipfs_client(), metadata_hash)
        metadata = metadata.decode("utf-8")
        return OrganizationMetadata.from_json(json.loads(metadata))

    def _get_organization_registration(self, org_id):
        params = [type_converter("bytes32")(org_id)]
        result = self.call_contract_command(
            "Registry", "getOrganizationById", params)
        if result[0] == False:
            raise Exception("Cannot find  Organization with id=%s" % (
                self.args.org_id))
        return {"orgMetadataURI": result[2]}

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
        metadata_uri = ipfs_utils.hash_to_bytesuri(
            self._publish_metadata_in_ipfs(self.args.metadata_file))
        #tags = self._get_converted_tags()
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id), metadata_uri]
        self.transact_contract_command(
            "Registry", "createServiceRegistration", params)

    def publish_metadata_in_ipfs_and_update_registration(self):
        # first we check that we do not change payment_address or group_id in existed payment groups
        self._validate_service_group_with_org_group_and_update_group_id(
            self.args.org_id, self.args.metadata_file)
        metadata_uri = ipfs_utils.hash_to_bytesuri(
            self._publish_metadata_in_ipfs(self.args.metadata_file))
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id), metadata_uri]
        self.transact_contract_command(
            "Registry", "updateServiceRegistration", params)

    #def _get_params_for_tags_update(self):
    #    tags = self._get_converted_tags()
    #    params = [type_converter("bytes32")(self.args.org_id), type_converter(
    #        "bytes32")(self.args.service_id), tags]
    #    return params

    def metadata_add_tags(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        [metadata.add_tag(tag) for tag in self.args.tags]
        metadata.save_pretty(self.args.metadata_file)

    def metadata_remove_tags(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        [metadata.remove_tag(tag) for tag in self.args.tags]
        metadata.save_pretty(self.args.metadata_file)

    def update_registration_add_tags(self):
        self._printout("This command has been deprecated. Please use `snet service metadata-add-tags` instead")

    def update_registration_remove_tags(self):
        self._printout("This command has been deprecated. Please use `snet service metadata-remove-tags` instead")

    def _get_service_registration(self):
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id)]
        rez = self.call_contract_command(
            "Registry", "getServiceRegistrationById", params)
        if rez[0] == False:
            raise Exception("Cannot find Service with id=%s in Organization with id=%s" % (
                self.args.service_id, self.args.org_id))
        return {"metadataURI": rez[2]}

    def _get_service_metadata_from_registry(self):
        rez = self._get_service_registration()
        metadata_hash = ipfs_utils.bytesuri_to_hash(rez["metadataURI"])
        metadata = ipfs_utils.get_from_ipfs_and_checkhash(
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
        if self.args.group_name != None:
            groups = {self.args.group_name: metadata.get_all_endpoints_for_group(
                self.args.group_name)}
        else:
            groups = metadata.get_all_group_endpoints()
        service_status = defaultdict(list)
        for name, group_endpoints in groups.items():
            for endpoint in group_endpoints:
                status = "Available" if self._service_status(
                    url=endpoint) else "Not Available"
                service_status[name].append(
                    {"endpoint": endpoint, "status": status})
        if service_status == {}:
            self._printout(
                "Error: No endpoints found to check service status.")
            return
        self._pprint(service_status)

    def print_service_tags_from_registry(self):
        metadata = self._get_service_metadata_from_registry()
        self._printout(" ".join(metadata.get_tags()))

    def extract_service_api_from_metadata(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        ipfs_utils.safe_extract_proto_from_ipfs(self._get_ipfs_client(
        ), metadata["model_ipfs_hash"], self.args.protodir)

    def extract_service_api_from_registry(self):
        metadata = self._get_service_metadata_from_registry()
        ipfs_utils.safe_extract_proto_from_ipfs(self._get_ipfs_client(
        ), metadata["model_ipfs_hash"], self.args.protodir)

    def delete_service_registration(self):
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id)]
        self.transact_contract_command(
            "Registry", "deleteServiceRegistration", params)
