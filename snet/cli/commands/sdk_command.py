import os
from pathlib import Path, PurePath

from snet.cli.utils.utils import compile_proto, download_and_safe_extract_proto, check_training_in_proto
from snet.cli.commands.mpe_service import MPEServiceCommand


class SDKCommand(MPEServiceCommand):
    def generate_client_library(self):

        if os.path.isabs(self.args.protodir):
            client_libraries_base_dir_path = PurePath(self.args.protodir)
        else:
            cur_dir_path = PurePath(os.getcwd())
            client_libraries_base_dir_path = cur_dir_path.joinpath(self.args.protodir)

        os.makedirs(client_libraries_base_dir_path, exist_ok=True)

        # Create service client libraries path
        library_org_id = self.args.org_id
        library_service_id = self.args.service_id

        library_dir_path = client_libraries_base_dir_path.joinpath(library_org_id, library_service_id, "python")

        metadata = self._get_service_metadata_from_registry()
        service_api_source = metadata.get("service_api_source") or metadata.get("model_ipfs_hash")

        # Receive proto files
        download_and_safe_extract_proto(service_api_source, library_dir_path, self._get_ipfs_client())

        training_added = check_training_in_proto(library_dir_path)

        # Compile proto files
        compile_proto(Path(library_dir_path), library_dir_path, add_training = training_added)

        self._printout(
            'client libraries for service with id "{}" in org with id "{}" generated at {}'.format(library_service_id,
                                                                                                   library_org_id,
                                                                                                   library_dir_path))
