from snet import sdk
import examples_service_pb2_grpc
import examples_service_pb2


def verify_when_no_open_channel(service_client):
    channels = service_client.load_open_channels()
    assert len(channels) == 0


def open_first_channel(service_client):
    channel = service_client.open_channel(123456, 33333)
    assert channel.channel_id == 0
    assert channel.state['nonce'] == 0
    assert channel.state['last_signed_amount'] == 0


def first_call_to_service_after_opening_first_channel(service_client):
    request = examples_service_pb2.Numbers(a=20, b=3)
    result = service_client.service.mul(request)


def verify_channel_state_after_opening_first_channel_and_first_call_to_service(service_client):
    service_client.update_channel_states()
    channels = service_client.load_open_channels()

    assert channels[0].channel_id == 0
    assert channels[0].state['nonce'] == 0
    assert channels[0].state['last_signed_amount'] == 1000


def second_call_to_service_after_opening_first_channel(service_client):
    request = examples_service_pb2.Numbers(a=20, b=3)
    result = service_client.service.mul(request)


def verify_channel_state_after_opening_first_channel_and_second_call_to_service(service_client):
    service_client.update_channel_states()
    channels = service_client.load_open_channels()

    assert channels[0].channel_id == 0
    assert channels[0].state['nonce'] == 0
    assert channels[0].state['last_signed_amount'] == 2000


def open_second_channel(service_client):
    channel = service_client.open_channel(1234321, 123456)
    assert channel.channel_id == 1
    assert channel.state['nonce'] == 0
    assert channel.state['last_signed_amount'] == 0


def verify_number_of_channel_after_opening_second_channel(service_client):
    service_client.update_channel_states()
    channels = service_client.load_open_channels()

    assert channels[0].channel_id == 0
    assert channels[0].state['nonce'] == 0
    assert channels[0].state['last_signed_amount'] == 2000
    assert channels[1].channel_id == 1
    assert channels[1].state['nonce'] == 0
    assert channels[1].state['last_signed_amount'] == 0


def first_call_to_service_after_opening_second_channel(service_client):
    request = examples_service_pb2.Numbers(a=20, b=3)

    result = service_client.service.mul(request)


def verify_channel_state_after_opening_second_channel_and_first_call_to_service(service_client):
    service_client.update_channel_states()

    channels = service_client.load_open_channels()
    assert channels[0].channel_id == 0
    assert channels[0].state['nonce'] == 0
    assert channels[0].state['last_signed_amount'] == 3000
    assert channels[1].channel_id == 1
    assert channels[1].state['nonce'] == 0
    assert channels[1].state['last_signed_amount'] == 0


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
        "ipfs_rpc_endpoint": "http://localhost:5002"

    }

    snet_sdk = sdk.SnetSDK(config)
    service_client = snet_sdk.create_service_client(org_id, service_id, examples_service_pb2_grpc.CalculatorStub,
                                                    group_name=group_name)

    verify_when_no_open_channel(service_client)
    open_first_channel(service_client)
    first_call_to_service_after_opening_first_channel(service_client)
    verify_channel_state_after_opening_first_channel_and_first_call_to_service(service_client)
    second_call_to_service_after_opening_first_channel(service_client)
    verify_channel_state_after_opening_first_channel_and_second_call_to_service(service_client)
    open_second_channel(service_client)
    verify_number_of_channel_after_opening_second_channel(service_client)
    first_call_to_service_after_opening_second_channel(service_client)
    verify_channel_state_after_opening_second_channel_and_first_call_to_service(service_client)


if __name__ == '__main__':
    test_sdk()
