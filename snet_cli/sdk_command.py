from snet_cli.commands import BlockchainCommand
import os 
from pathlib import Path, PurePath
from tempfile import TemporaryDirectory

from snet_cli.utils import type_converter, bytes32_to_str, compile_proto
from snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash, safe_extract_proto_from_ipfs
from snet_cli.mpe_service_metadata import mpe_service_metadata_from_json

class SDKCommand(BlockchainCommand):
    def generate_client_library(self):
        cur_dir_path = PurePath(os.path.dirname(os.path.realpath(__file__)))

        if not self.args.protodir:
            client_libraries_base_dir_path = cur_dir_path.parent.joinpath("client_libraries")
            if not os.path.exists(client_libraries_base_dir_path):
                os.makedirs(client_libraries_base_dir_path)
        else:
            if os.path.isabs(self.args.protodir):
                client_libraries_base_dir_path = PurePath(self.args.protodir)
            else: 
                client_libraries_base_dir_path = PurePath(os.getcwd()).joinpath(self.args.protodir)

            if not os.path.isdir(client_libraries_base_dir_path):
                self._error("directory {} does not exist. Please make sure that the specified path exists".format(client_libraries_base_dir_path))

        # Check that service exists
        (found, org_service_list) = self.call_contract_command("Registry", "listServicesForOrganization", [type_converter("bytes32")(self.args.org_id)])
        if not found:
            self._error("organization {} does not exist".format(self.args.org_id))

        org_service_list = list(map(bytes32_to_str, org_service_list))

        if self.args.service_id not in org_service_list:
            self._error("service {} does not exist in organization {}".format(self.args.service_id, self.args.org_id))

        # Create service client libraries path
        library_language = self.args.language
        library_org_id = self.args.org_id
        library_service_id = self.args.service_id

        library_dir_path = client_libraries_base_dir_path.joinpath(library_language, library_org_id, library_service_id)

        # Download and extract proto files
        ipfs_metadata_hash = bytesuri_to_hash(self.call_contract_command("Registry", "getServiceRegistrationById", [type_converter("bytes32")(self.args.org_id), type_converter("bytes32")(self.args.service_id)])[2])
        metadata = get_from_ipfs_and_checkhash(self._get_ipfs_client(), ipfs_metadata_hash)
        metadata = metadata.decode("utf-8")
        metadata = mpe_service_metadata_from_json(metadata)
        model_ipfs_hash = metadata["model_ipfs_hash"]

        with TemporaryDirectory() as temp_dir: 
            temp_dir_path = PurePath(temp_dir)
            proto_temp_dir_path = temp_dir_path.joinpath(library_language, library_org_id, library_service_id)
            safe_extract_proto_from_ipfs(self._get_ipfs_client(), model_ipfs_hash, proto_temp_dir_path)

        # Compile proto files
            compile_proto(Path(proto_temp_dir_path), library_dir_path)

        self._printout('client libraries for service with id "{}" in org with id "{}" generated at {}'.format(library_service_id, library_org_id, library_dir_path))
