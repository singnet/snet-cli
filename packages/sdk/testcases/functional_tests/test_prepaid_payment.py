from snet import sdk
import examples_service_pb2_grpc
import examples_service_pb2


def use_freecalls(service_client):
    service_call(service_client, a=1, b=2)
    service_call(service_client, a=1, b=2)

def open_first_channel(service_client):
    channel = service_client.open_channel(123456, 33333)
    assert channel.channel_id == 0
    assert channel.state['nonce'] == 0
    assert channel.state['last_signed_amount'] == 0

def service_call(service_client, a, b):
    request = examples_service_pb2.Numbers(a=a, b=b)
    result = service_client.service.mul(request)
    assert result.value == a*b

def make_cuncurrent_calls(service_client):
    service_call(service_client, a=1, b=2)
    service_call(service_client, a=1, b=2)

def check_channel_status(service_client):
    service_client.update_channel_states()
    channels = service_client.load_open_channels()

    assert channels[0].channel_id == 0
    assert channels[0].state['last_signed_amount'] == 3000


def test_sdk():
    org_id = "test_org"
    service_id = "test_service"
    group_name = "default_group"

    config = {
        "private_key": "0xc71478a6d0fe44e763649de0a0deb5a080b788eefbbcf9c6f7aef0dd5dbd67e0",
        "eth_rpc_endpoint": "http://localhost:8545",
        "mpe_contract_address": "0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e",
        "registry_contract_address": "0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2",
        "token_contract_address": "0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14",
        "ipfs_rpc_endpoint": "http://localhost:5002",
        "free_call_auth_token-bin": "f2548d27ffd319b9c05918eeac15ebab934e5cfcd68e1ec3db2b927653892959012b48da17a7973d57f72fac3c1eccd97862a4fa953c3726da65dec42f5989ee1b",
        "free-call-token-expiry-block": 172800,
        "email": "test@test.com"
    }

    snet_sdk = sdk.SnetSDK(config)
    service_client = snet_sdk.create_service_client(org_id, service_id, examples_service_pb2_grpc.CalculatorStub,
                                                    group_name=group_name, concurrent_calls=3)
    use_freecalls(service_client)
    open_first_channel(service_client)
    make_cuncurrent_calls(service_client)
    check_channel_status(service_client)


if __name__ == '__main__':
    test_sdk()
