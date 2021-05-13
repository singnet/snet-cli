import importlib

import grpc
import web3
from snet.snet_cli.utils.utils import RESOURCES_PATH, add_to_path


class ConcurrencyManager:
    def __init__(self, concurrent_calls):
        self.__concurrent_calls = concurrent_calls
        self.__token = ''
        self.__planned_amount = 0
        self.__used_amount = 0

    @property
    def concurrent_calls(self):
        return self.__concurrent_calls

    def get_token(self, service_client, channel, service_call_price):
        if len(self.__token) == 0:
            self.__token = self.__get_token(service_client, channel, service_call_price)
        elif self.__used_amount >= self.__planned_amount:
            self.__token = self.__get_token(service_client, channel, service_call_price, new_token=True)
        return self.__token

    def __get_token(self, service_client, channel, service_call_price, new_token=False):
        if not new_token:
            amount = channel.state["last_signed_amount"]
            if amount != 0:
                try:
                    token_reply = self.__get_token_for_amount(service_client, channel, amount)
                    planned_amount = token_reply.planned_amount
                    used_amount = token_reply.used_amount
                    if planned_amount - used_amount > 0:
                        self.__used_amount = used_amount
                        self.__planned_amount = planned_amount
                        return token_reply.token
                except grpc.RpcError as e:
                    if e.details() != "Unable to retrieve planned Amount ":
                        raise

        amount = channel.state["last_signed_amount"] + service_call_price
        token_reply = self.__get_token_for_amount(service_client, channel, amount)
        self.__used_amount = token_reply.used_amount
        self.__planned_amount = token_reply.planned_amount
        return token_reply.token

    def __get_stub_for_get_token(self, service_client):
        grpc_channel = service_client.get_grpc_base_channel()
        with add_to_path(str(RESOURCES_PATH.joinpath("proto"))):
            token_service_pb2_grpc = importlib.import_module("token_service_pb2_grpc")
        return token_service_pb2_grpc.TokenServiceStub(grpc_channel)

    def __get_token_for_amount(self, service_client, channel, amount):
        nonce = channel.state["nonce"]
        stub = self.__get_stub_for_get_token(service_client)
        with add_to_path(str(RESOURCES_PATH.joinpath("proto"))):
            token_service_pb2 = importlib.import_module("token_service_pb2")
        current_block_number = service_client.sdk_web3.eth.getBlock("latest").number
        message = web3.Web3.soliditySha3(
            ["string", "address", "uint256", "uint256", "uint256"],
            ["__MPE_claim_message", service_client.mpe_address, channel.channel_id, nonce, amount]
        )
        mpe_signature = service_client.generate_signature(message)
        message = web3.Web3.soliditySha3(
            ["bytes", "uint256"],
            [mpe_signature, current_block_number]
        )
        sign_mpe_signature = service_client.generate_signature(message)

        request = token_service_pb2.TokenRequest(
            channel_id=channel.channel_id, current_nonce=nonce, signed_amount=amount,
            signature=bytes(sign_mpe_signature), claim_signature=bytes(mpe_signature),
            current_block=current_block_number)
        token_reply = stub.GetToken(request)
        return token_reply

    def record_successful_call(self):
        self.__used_amount += 1
