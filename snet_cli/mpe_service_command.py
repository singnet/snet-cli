from snet_cli.commands    import BlockchainCommand
import snet_cli.utils_ipfs as utils_ipfs
from snet_cli.mpe_service_metadata import MPEServiceMetadata, load_mpe_service_metadata, mpe_service_metadata_from_json
from snet_cli.utils import type_converter
from snet_cli.utils_ipfs import hash_to_bytesuri, bytesuri_to_hash, get_from_ipfs_and_checkhash
import web3

class MPEServiceCommand(BlockchainCommand):
        
    # I. Low level functions
    
    # publis proto files in ipfs and print hash
    def publish_proto_in_ipfs(self):
        ipfs_hash_base58 = utils_ipfs.publish_proto_in_ipfs(self._get_ipfs_client(), self.args.protodir)
        self._printout(ipfs_hash_base58)

    def publish_proto_metadata_init(self):
        ipfs_hash_base58 = utils_ipfs.publish_proto_in_ipfs(self._get_ipfs_client(), self.args.protodir)
        metadata    = MPEServiceMetadata()
        mpe_address = self.get_mpe_address()
        metadata.set_simple_field("model_ipfs_hash",              ipfs_hash_base58)
        metadata.set_simple_field("mpe_address",                  mpe_address)
        metadata.set_simple_field("display_name",                 self.args.display_name)
        metadata.set_simple_field("encoding",                     self.args.encoding)
        metadata.set_simple_field("service_type",                 self.args.service_type)
        metadata.set_simple_field("payment_expiration_threshold", self.args.payment_expiration_threshold)
        self._metadata_add_group(metadata)
        metadata.save_pretty(self.args.metadata_file)

    def metadata_set_fixed_price(self):        
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.set_fixed_price_in_cogs(self.args.price)
        metadata.save_pretty(self.args.metadata_file)

    def _metadata_add_group(self, metadata):
        if (not web3.eth.is_checksum_address(self.args.payment_address)):
            raise Exception("payment_address parameter is not a valid Ethereum checksum address")
        metadata.add_group(self.args.group_name, self.args.payment_address)

    def metadata_add_group(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        self._metadata_add_group(metadata)
        metadata.save_pretty(self.args.metadata_file)

    # metadata add endpoint to the group
    def metadata_add_endpoints(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.load(self.args.metadata_file)
        group_name = metadata.get_group_name_nonetrick(self.args.group_name)
        for endpoint in self.args.endpoints:
            metadata.add_endpoint(group_name, endpoint)
        metadata.save_pretty(self.args.metadata_file)

    def _publish_metadata_in_ipfs(self, metadata_file):
        metadata = load_mpe_service_metadata(metadata_file)
        return self._get_ipfs_client().add_bytes(metadata.get_json().encode("utf-8"))
    
    # publish metadata in ipfs and print hash
    def publish_metadata_in_ipfs(self):
        self._printout( self._publish_metadata_in_ipfs(self.args.metadata_file) )
    
    def _get_converted_tags(self):
        return [type_converter("bytes32")(tag) for tag in self.args.tags]
    
    def publish_service_with_metadata(self):
        metadata_uri     = hash_to_bytesuri( self._publish_metadata_in_ipfs(self.args.metadata_file))
        tags             = self._get_converted_tags()
        params           = [type_converter("bytes32")(self.args.organization), type_converter("bytes32")(self.args.service), metadata_uri, tags]
        self.transact_contract_command("Registry", "createServiceRegistration", params)

    def publish_metadata_in_ipfs_and_update_registration(self):
        metadata_uri     = hash_to_bytesuri( self._publish_metadata_in_ipfs(self.args.metadata_file))
        params           = [type_converter("bytes32")(self.args.organization), type_converter("bytes32")(self.args.service), metadata_uri]
        self.transact_contract_command("Registry", "updateServiceRegistration", params)

    def _get_params_for_tags_update(self):
        tags             = self._get_converted_tags()
        params           = [type_converter("bytes32")(self.args.organization), type_converter("bytes32")(self.args.service), tags]
        return params
    
    def update_registration_add_tags(self):
        params = self._get_params_for_tags_update()
        self.transact_contract_command("Registry", "addTagsToServiceRegistration", params)

    def update_registration_remove_tags(self):
        params = self._get_params_for_tags_update()
        self.transact_contract_command("Registry", "removeTagsFromServiceRegistration", params)
        
    def _get_service_registration(self):
        params = [type_converter("bytes32")(self.args.organization), type_converter("bytes32")(self.args.service)]
        rez = self.call_contract_command("Registry", "getServiceRegistrationByName", params)
        if (rez[0] == False):
            raise Exception("Cannot find Service %s in Organization %s"%(self.args.service, self.args.organization))
        return rez
        
    def print_service_metadata_from_registry(self):
        rez           = self._get_service_registration()
        metadata_hash = bytesuri_to_hash(rez[2])
        metadata      = get_from_ipfs_and_checkhash(self._get_ipfs_client(), metadata_hash)
        metadata      = metadata.decode("utf-8")
        metadata      = mpe_service_metadata_from_json(metadata)
        self._printout(metadata.get_json_pretty())

    def print_service_tags_from_registry(self):
        rez  = self._get_service_registration()
        tags = rez[3]
        tags = [tag.rstrip(b"\0").decode('utf-8') for tag in tags]
        self._printout(" ".join(tags))

    def delete_service_registration(self):
        params = [type_converter("bytes32")(self.args.organization), type_converter("bytes32")(self.args.service)]
        self.transact_contract_command("Registry", "deleteServiceRegistration", params)
