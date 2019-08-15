import sys
from snet.sdk import SnetSDK

config = {
    "private_key": "0xc71478a6d0fe44e763649de0a0deb5a080b788eefbbcf9c6f7aef0dd5dbd67e0",
    "eth_rpc_endpoint": "http://localhost:8545",
    "ipfs_rpc_endpoint": "http://localhost:5002",
    "token_contract_address": "0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14",
    "registry_contract_address": "0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2",
    "mpe_contract_address": "0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e"
}

sdk = SnetSDK(config)

import ExampleService_pb2
import ExampleService_pb2_grpc


# Examples using the "get_method" utility function
service_client = sdk.create_dynamic_service_client("testo", "tests")

method, request_type, _ = service_client.get_method("classify")
print("Performing request")
request = request_type()
result = method(request)
print("Result: {}".format(result))


# Example using the "get_method" utility function and a fully qualified method name ([<package>].service.method)
method, request_type, _ = service_client.get_method("ExampleService.classify")
print("Performing request")
request = request_type()
result = method(request)
print("Result: {}".format(result))


# Example without the get_method utility function
request = service_client.message.ClassifyRequest()
print("Performing request")
result = service_client.service.ExampleService.service.classify(request)
print("Result: {}".format(result))


# Examples with static service client
service_client = sdk.create_service_client(
    "testo", "tests", ExampleService_pb2_grpc.ExampleServiceStub)
request = ExampleService_pb2.ClassifyRequest()
print("Performing request")
result = service_client.service.classify(request)
print("Result: {}".format(result))
