from snet import sdk
import examples_service_pb2
import examples_service_pb2_grpc
import threading



def service_call(service_client, token, channel, a, b):
    service_client.set_concurrency_token_and_channel(token, channel)
    request = examples_service_pb2.Numbers(a=a, b=b)
    result = service_client.service.mul(request)
    assert result.value == a * b


def test_sdk():
    org_id = "6ce80f485dae487688c3a083688819bb"
    service_id = "test_freecall"
    group_name = "default_group"

    config = {
        "private_key": "0x484573a7949da33d9aceeba372fc697532fdb69278318c03d04418a1af8a6208",
        "eth_rpc_endpoint": "https://ropsten.infura.io/v3/09027f4a13e841d48dbfefc67e7685d5",
        "mpe_contract_address": "0x8fb1dc8df86b388c7e00689d1ecb533a160b4d0c",
        "registry_contract_address": "0x663422c6999ff94933dbcb388623952cf2407f6f",
        "token_contract_address": "0xb97E9bBB6fd49865709d3F1576e8506ad640a13B",
        "ipfs_rpc_endpoint": "http://ipfs.singularitynet.io:80",
        "free_call_auth_token-bin": "",
        "free-call-token-expiry-block": 9808238,
        "email": "ichbinvivek@gmail.com"
    }
    snet_sdk = sdk.SnetSDK(config)
    service_client = snet_sdk.create_service_client(org_id, service_id, examples_service_pb2_grpc.CalculatorStub,
                                                    group_name=group_name, concurrent_calls=2)
    token, channel = service_client.get_concurrency_token_and_channel()
    try:
        thread_1 = threading.Thread(target=service_call, args=(service_client, token, channel, 2, 3), name="thread_1")
        thread_2 = threading.Thread(target=service_call, args=(service_client, token, channel, 4, 5), name="thread_2")
        thread_1.start()
        thread_2.start()
        thread_1.join()
        thread_2.join()
    except Exception as e:
        print("threading failed", e)


if __name__ == '__main__':
    test_sdk()
