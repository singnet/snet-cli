from pathlib import Path, PurePath
from types import SimpleNamespace

from snet.sdk.service_client import ServiceClient
from snet.snet_cli.utils import get_contract_object, compile_proto
from snet.snet_cli.utils_proto import import_all_grpc_methods_from_dir
from snet.snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash, safe_extract_proto_from_ipfs

class DynamicServiceClient:
    def __init__(self, sdk, metadata, group, org_id, service_id, grpc_output_path, strategy, options):
        safe_extract_proto_from_ipfs(sdk.ipfs_client, metadata['model_ipfs_hash'], grpc_output_path, overwrite=True)
        compile_proto(Path(grpc_output_path), grpc_output_path)
        self._services = import_all_grpc_methods_from_dir(grpc_output_path)

        for fully_qualified_method_name, (stub, request, response) in self._services.items():
            package = None
            try:
                package, service, method = fully_qualified_method_name.split(".")
            except:
                service, method = fully_qualified_method_name.split(".")
            if package:
                package_object = getattr(self, package, None)
                if package_object is None:
                    setattr(self, package, SimpleNamespace())
                    package_object = getattr(self, package)
                    setattr(package_object, "service", SimpleNamespace())
                    setattr(package_object, "message", SimpleNamespace())
                setattr(package_object.service, service, ServiceClient(sdk, metadata, group, stub, strategy, options))
                setattr(package_object.message, request.DESCRIPTOR.name, request)
                setattr(package_object.message, response.DESCRIPTOR.name, response)
            else:
                if not hasattr(self, "service"):
                    self.service = SimpleNamespace()
                if not hasattr(self, "message"):
                    self.message = SimpleNamespace()
                setattr(self.service, service, ServiceClient(sdk, metadata, group, stub, strategy, options))
                setattr(self.message, request.DESCRIPTOR.name, request)
                setattr(self.message, response.DESCRIPTOR.name, response)


    # Given a method name, returns the method function for the ServiceClient instance of the service to which that method belongs, and its request and response types
    def get_method(self, method_name):
        request_type = None
        response_type = None
        method_fields = method_name.split(".")
        if len(method_fields) == 1: # User is providing just the name of the method
            for fully_qualified_method_name, (stub, request, response) in self._services.items():
                package = None
                try:
                    package, service, method = fully_qualified_method_name.split(".")
                except:
                    service, method = fully_qualified_method_name.split(".")
                if method == method_name:
                    if request_type is not None or response_type is not None:
                        raise Exception("Multiple methods found for method {}. Please specify the fully qualified method name (<package>.<service>.<method>)".format(method_name))
                    else:
                        if package is None:
                            service_object = getattr(self.service, service).service
                            method_function = getattr(service_object, method)
                            request_type = request
                            response_type = response
                        else:
                            services_object = getattr(self, package, self).service
                            service_object = getattr(services_object, service).service
                            method_function = getattr(service_object, method)
                            request_type = request
                            response_type = response
        else: # User is providing a fully qualified method name (<package>.<service>.<method>)
            if method_name in self._services:
                package = None
                try:
                    package, service, method = method_fields
                except:
                    service, method = method_fields

                if package is None:
                    service_object = getattr(self.service, service).service
                    method_function = getattr(service_object, method)
                    request_type = self._services[method_name][1]
                    response_type = self._services[method_name][2]
                else:
                    services_object = getattr(self, package, self).service
                    service_object = getattr(services_object, service).service
                    method_function = getattr(service_object, method)
                    request_type = self._services[method_name][1]
                    response_type = self._services[method_name][2]
            else:
                raise Exception("No method found for fully qualified name {}".format(method_name))

        if request_type is None or response_type is None:
            raise Exception("No method {} found for given service".format(method_name))

        return method_function, request_type, response_type
