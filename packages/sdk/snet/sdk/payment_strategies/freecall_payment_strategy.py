from urllib.parse import urlparse

import grpc
import web3
from snet.sdk.payment_strategies.default import PaymentChannelManagementStrategy
from snet.sdk.payment_strategies.payment_staregy import PaymentStrategy
from snet.snet_cli.resources.proto import state_service_pb2, state_service_pb2_grpc


class FreeCallPaymentStrategy(PaymentStrategy):

    def is_free_call_available(self, email, token_for_free_call, token_expiry_date_block, signature,
                               current_block_number, daemon_endpoint):

        request = state_service_pb2.FreeCallStateRequest()
        request.user_id = email
        request.token_for_free_call = token_for_free_call
        request.token_expiry_date_block = token_expiry_date_block
        request.signature = signature
        request.current_block = current_block_number

        endpoint_object = urlparse(daemon_endpoint)
        if endpoint_object.port is not None:
            channel_endpoint = endpoint_object.hostname + ":" + str(endpoint_object.port)
        else:
            channel_endpoint = endpoint_object.hostname

        if endpoint_object.scheme == "http":
            channel = grpc.insecure_channel(channel_endpoint)
        elif endpoint_object.scheme == "https":
            channel = grpc.secure_channel(channel_endpoint, grpc.ssl_channel_credentials())
        else:
            raise ValueError('Unsupported scheme in service metadata ("{}")'.format(endpoint_object.scheme))

        stub = state_service_pb2_grpc.FreeCallStateServiceStub(channel)
        response = stub.GetFreeCallsAvailable(request)
        if response.free_calls_available > 0:
            return True
        return False


    def get_payment_metadata(self, service_client):

        org_id, service_id, group_id, daemon_endpoint = service_client.get_service_details()
        email, token_for_free_call, token_expiry_date_block = service_client.get_free_call_config()

        current_block_number = service_client.get_current_block_number()

        message = web3.Web3.soliditySha3(
            ["string", "string", "string", "string", "string", "uint256", "bytes32"],
            ["__prefix_free_trial", email, org_id, service_id, group_id, current_block_number,
             token_for_free_call]
        )
        signature = service_client.generate_signature(message)

        if self.is_free_call_available(email, token_for_free_call, token_expiry_date_block, signature,
                                       current_block_number, daemon_endpoint):
            metadata = [("snet-free-call-auth-token-bin", token_for_free_call),
                        ("snet-free-call-token-expiry-block", str(token_expiry_date_block)),
                        ("snet-payment-type", "free-call"),
                        ("snet-free-call-user-id", "sumitk002@gmail.com"),
                        ("snet-current-block-number", str(current_block_number)),
                        ("snet-payment-channel-signature-bin", signature)
                        ]
        else:
            payment_strategy = PaymentChannelManagementStrategy()
            metadata = payment_strategy.get_payment_metadata(service_client)

        return metadata

    def select_channel(self,service_client):
        pass

