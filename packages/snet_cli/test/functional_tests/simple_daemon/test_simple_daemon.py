from concurrent import futures
import time
import web3

from snet_cli.config import Config

from snet_cli.commands.mpe_channel import MPEChannelCommand
from snet.snet_cli.utils.utils import compile_proto, DefaultAttributeObject


compile_proto("../service_spec1", ".", proto_file = "ExampleService.proto")
compile_proto("../../../snet/snet_cli/resources/proto/", ".", proto_file = "state_service.proto")
compile_proto("../../../snet/snet_cli/resources/proto/", ".", proto_file = "control_service.proto")
PRICE = 10000

import grpc

import ExampleService_pb2
import ExampleService_pb2_grpc

import state_service_pb2
import state_service_pb2_grpc

import control_service_pb2
import control_service_pb2_grpc

payments_unclaimed   = dict()
payments_in_progress = dict()

# we use MPEChannelCommand._get_channel_state_from_blockchain to get channel state from blockchain
# we need it to remove already claimed payments from payments_in_progress
# remove all payments_in_progress with nonce < blockchain nonce
def remove_already_claimed_payments():
    conf   = Config()
    cc = MPEChannelCommand(conf, DefaultAttributeObject())
    to_remove = []
    for channel_id in payments_in_progress:
        blockchain = cc._get_channel_state_from_blockchain(channel_id)
        if (blockchain["nonce"] > payments_in_progress[channel_id]["nonce"]):
            to_remove.append(channel_id)
    for channel_id in to_remove:
        print("remove payment for channel %i from payments_in_progress"%channel_id)
        del payments_in_progress[channel_id]

def get_current_channel_state(channel_id):
    if (channel_id in payments_unclaimed):
        nonce         = payments_unclaimed[channel_id]["nonce"]
        amount        = payments_unclaimed[channel_id]["amount"]
        signature     = payments_unclaimed[channel_id]["signature"]
    else:
        nonce  = 0
        amount = 0
        signature = "".encode("ascii")
    return nonce, amount, signature


class ExampleService(ExampleService_pb2_grpc.ExampleServiceServicer):
    def classify(self, request, context):
        metadata = dict(context.invocation_metadata())
        channel_id = int(metadata["snet-payment-channel-id"])
        nonce      = int(metadata["snet-payment-channel-nonce"])
        amount     = int(metadata["snet-payment-channel-amount"])
        signature  = metadata["snet-payment-channel-signature-bin"]
        payment = {"channel_id": channel_id, "nonce": nonce, "amount": amount, "signature": signature}

        # we check nonce and amount, but we don't check signature
        current_nonce, current_signed_amount, _ = get_current_channel_state(channel_id)

        if (current_nonce != nonce):
            raise Exception("nonce is incorrect")

        if (current_signed_amount + PRICE != amount):
            raise Exception("Signed amount is incorrect %i vs %i"%(current_signed_amount + PRICE, amount))

        payments_unclaimed[channel_id] = payment
        return ExampleService_pb2.ClassifyResponse(predictions=["prediction1", "prediction2" ], confidences=[0.42, 0.43], binary_field = int(12345**5).to_bytes(10,byteorder='big'))


class PaymentChannelStateService(state_service_pb2_grpc.PaymentChannelStateServiceServicer):
    def GetChannelState(self, request, context):
        channel_id = int.from_bytes(request.channel_id, byteorder='big')
        nonce, amount, signature = get_current_channel_state(channel_id)
        if (channel_id in payments_in_progress):
            if (payments_in_progress[channel_id]["nonce"] != nonce - 1):
                raise Exception("Bad payment in payments_in_progress")
            return state_service_pb2.ChannelStateReply(current_nonce           = web3.Web3.toBytes(nonce),
                                                       current_signed_amount   = web3.Web3.toBytes(amount),
                                                       current_signature       = signature,
                                                       old_nonce_signed_amount = web3.Web3.toBytes(payments_in_progress[channel_id]["amount"]),
                                                       old_nonce_signature     = payments_in_progress[channel_id]["signature"])
        return state_service_pb2.ChannelStateReply(current_nonce         = web3.Web3.toBytes(nonce),
                                                   current_signed_amount = web3.Web3.toBytes(amount),
                                                   current_signature     = signature)


class ProviderControlService(control_service_pb2_grpc.ProviderControlServiceServicer):
    def GetListUnclaimed(self, request, context):
        payments = []
        for channel_id in payments_unclaimed:
            nonce  = payments_unclaimed[channel_id]["nonce"]
            amount = payments_unclaimed[channel_id]["amount"]
            payment = control_service_pb2.PaymentReply(
                           channel_id    = web3.Web3.toBytes(channel_id),
                           channel_nonce = web3.Web3.toBytes(nonce),
                           signed_amount = web3.Web3.toBytes(amount))
            payments.append(payment)
        return control_service_pb2.PaymentsListReply(payments = payments)

    def GetListInProgress(self, request, context):
        remove_already_claimed_payments()

        payments = []
        for channel_id in payments_in_progress:
            p = payments_in_progress[channel_id]
            payment = control_service_pb2.PaymentReply(
                           channel_id    = web3.Web3.toBytes(channel_id),
                           channel_nonce = web3.Web3.toBytes(p["nonce"]),
                           signed_amount = web3.Web3.toBytes(p["amount"]),
                           signature     = p["signature"])
            payments.append(payment)
        return control_service_pb2.PaymentsListReply(payments = payments)

    def StartClaim(self, request, context):
        remove_already_claimed_payments()

        channel_id = int.from_bytes(request.channel_id, byteorder='big')

        if (channel_id not in payments_unclaimed):
            raise Exception("channel_id not in payments_unclaimed")

        p = payments_unclaimed[channel_id]
        nonce     = p["nonce"]
        amount    = p["amount"]
        signature = p["signature"]
        payments_in_progress[channel_id] = p
        payments_unclaimed[channel_id] = {"nonce" : nonce + 1, "amount" : 0, "signature" : bytes(0)}

        return control_service_pb2.PaymentReply(
                        channel_id    = web3.Web3.toBytes(channel_id),
                        channel_nonce = web3.Web3.toBytes(nonce),
                        signed_amount = web3.Web3.toBytes(amount),
                        signature     = signature)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    ExampleService_pb2_grpc.add_ExampleServiceServicer_to_server(ExampleService(), server)
    state_service_pb2_grpc.add_PaymentChannelStateServiceServicer_to_server(PaymentChannelStateService(), server)
    control_service_pb2_grpc.add_ProviderControlServiceServicer_to_server(ProviderControlService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
        while True:
            time.sleep(60*60*24)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()

