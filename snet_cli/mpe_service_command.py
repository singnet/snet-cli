from snet_cli.commands    import BlockchainCommand
import snet_cli.utils_ipfs as utils_ipfs
from snet_cli.mpe_service_metadata import mpe_service_metadata, load_mpe_service_metadata
from snet_cli.utils import type_converter
import base58

class MPEServiceCommand(BlockchainCommand):
        
    # I. Low level functions
    
    # publis proto files in ipfs and print hash
    def publish_proto_in_ipfs(self):
        ipfs_hash_base58 = utils_ipfs.publish_proto_in_ipfs(self._get_ipfs_client(), self.args.protodir)
        self._printout(ipfs_hash_base58)
        
    # Init metadata and set model_ipfs_hash  
    def metadata_init(self):
        metadata = mpe_service_metadata()
        metadata.set_model_ipfs_hash(self.args.model_ipfs_hash)
        metadata.set_mpe_address(self.args.mpe_address)
        metadata.save(self.args.metadata_file)
        
    #  metadata set fixed price  
    def metadata_set_fixed_price(self):        
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.set_fixed_price(self.args.price)
        metadata.save(self.args.metadata_file)
        
    # metadata add group
    def metadata_add_group(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.add_group(self.args.group_name, self.args.payment_address)
        metadata.save(self.args.metadata_file)

    # metadata add endpoint to the group
    def metadata_add_endpoints(self):
        metadata = load_mpe_service_metadata(self.args.metadata_file)
        metadata.load(self.args.metadata_file)
        for endpoint in self.args.endpoints:
            metadata.add_endpoint(self.args.group_name, endpoint)
        metadata.save(self.args.metadata_file)

    def _publish_metadata_in_ipfs(self, metadata_file):
        metadata = load_mpe_service_metadata(metadata_file)
        return self._get_ipfs_client().add_bytes(metadata.get_json().encode("utf-8"))

    # publish metadata in ipfs and print hash
    def publish_metadata_in_ipfs(self):
        self._printout( self._publish_metadata_in_ipfs(self.args.metadata_file) ) 

    def _publish_metadata_in_ipfs_and_registry(self, registry_address, organization, service, metadata_file):
        metadata_hash_base58 = self._publish_metadata_in_ipfs(self.args.metadata_file)
        metadata_hash        = base58.b58decode(metadata_hash_base58)
        params = [type_converter("bytes32")(organization), type_converter("bytes32")(service), metadata_hash]
        self.transact_contract_command("Registry", registry_address, "setMetadataIPFSHashInServiceRegistration", params)
    
    def publish_metadata_in_ipfs_and_registry(self):
        self._publish_metadata_in_ipfs_and_registry(self.args.registry_address, self.args.organization, self.args.service, self.args.metadata_file)

    def _publish_service_with_metadata(self, registry_address, organization, service, service_path, tags, metadata_file):        
        # publish service with empty agent        
        tags = [type_converter("bytes32")(tag) for tag in tags]
        params = [type_converter("bytes32")(organization), type_converter("bytes32")(service), type_converter("bytes32")(service_path), "0x0000000000000000000000000000000000000000", tags]
        self.transact_contract_command("Registry", registry_address, "createServiceRegistration", params)
        self._publish_metadata_in_ipfs_and_registry(registry_address, organization, service, metadata_file)
    
    def publish_service_with_metadata(self):
        self._publish_service_with_metadata(self.args.registry_address, self.args.organization, self.args.service, self.args.service_path, self.args.tags, self.args.metadata_file)

    def _get_service_metadata_hash_from_registry(self, registry_address, organization, service):
        params = [type_converter("bytes32")(organization), type_converter("bytes32")(service)]
        rez = self.call_contract_command("Registry", self.args.registry_address, "getMetadataIPFSHash", params)
        if (rez[0] == False):
            raise Exception("Cannot find Service %s in Organization %s"%(self.args.service, self.args.organization))
        return base58.b58encode(rez[1]).decode("ascii")
    
    def get_service_metadata_hash_from_registry(self):
        self._printout(self._get_service_metadata_hash_from_registry(self.args.registry_address, self.args.organization, self.args.service))
        
    # II. High level functions
    def publish_service_fixed_price_single_group(self):
        
        # publish protobuf in ipfs
        model_ipfs_hash = utils_ipfs.publish_proto_in_ipfs(self._get_ipfs_client(), self.args.protodir)
        
        # create service metadata
        metadata = mpe_service_metadata()
        metadata.set_model_ipfs_hash(model_ipfs_hash)
        metadata.set_mpe_address(self.args.mpe_address)        
        metadata.set_fixed_price(self.args.price)
        metadata.add_group(self.args.group_name, self.args.payment_address)
        
        for endpoint in self.args.endpoints:            
            metadata.add_endpoint(self.args.group_name, endpoint)
            
        # save metadata in the file
        metadata.save(self.args.metadata_file)
        
        # publish service
        self._publish_service_with_metadata(self.args.registry_address, self.args.organization, self.args.service, self.args.service_path, self.args.tags, self.args.metadata_file)
            
