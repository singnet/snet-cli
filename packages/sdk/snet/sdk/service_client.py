import collections
import importlib

import grpc
import web3
from rfc3986 import urlparse
from eth_account.messages import defunct_hash_message

import snet.sdk.generic_client_interceptor as generic_client_interceptor
from snet.snet_cli.utils import RESOURCES_PATH, add_to_path


class _ClientCallDetails(
        collections.namedtuple(
            '_ClientCallDetails',
            ('method', 'timeout', 'metadata', 'credentials')),
        grpc.ClientCallDetails):
    pass


class ServiceClient:
    def __init__(self, sdk, metadata, group, service_stub, payment_channel_management_strategy, options):
        self.sdk = sdk
        self.options = options
        self.group = group
        self.metadata = metadata
        self.payment_channel_management_strategy = payment_channel_management_strategy
        self.expiry_threshold = self.metadata["payment_expiration_threshold"]
        self._base_grpc_channel = self._get_grpc_channel()
        self.grpc_channel = grpc.intercept_channel(self._base_grpc_channel, generic_client_interceptor.create(self._intercept_call))
        self.payment_channel_state_service_client = self._generate_payment_channel_state_service_client()
        self.service = self._generate_grpc_stub(service_stub)
        self.payment_channels = []
        self.last_read_block = 0


    def _generate_grpc_stub(self, service_stub):
        grpc_channel = self._base_grpc_channel
        disable_blockchain_operations = self.options.get("disable_blockchain_operations", False)
        if disable_blockchain_operations is False:
            grpc_channel = self.grpc_channel
        stub_instance = service_stub(grpc_channel)
        return stub_instance


    def _get_grpc_channel(self):
        endpoint = self.options.get("endpoint", None)
        if endpoint is None:
            endpoint = self.metadata.get_endpoints_for_group(self.group["group_name"])[0]
        endpoint_object = urlparse(endpoint)
        if endpoint_object.port is not None:
            channel_endpoint = endpoint_object.hostname + ":" + str(endpoint_object.port)
        else: 
            channel_endpoint = endpoint_object.hostname

        if endpoint_object.scheme == "http":
            return grpc.insecure_channel(channel_endpoint)
        elif endpoint_object.scheme == "https":
            return grpc.secure_channel(channel_endpoint, grpc.ssl_channel_credentials())
        else:
            raise ValueError('Unsupported scheme in service metadata ("{}")'.format(endpoint_object.scheme))


    def _get_service_call_metadata(self):
        channel = self.payment_channel_management_strategy.select_channel(self)
        amount = channel.state["last_signed_amount"] + int(self.metadata["pricing"]["price_in_cogs"])
        message = web3.Web3.soliditySha3(
            ["address", "uint256", "uint256", "uint256"],
            [self.sdk.mpe_contract.contract.address, channel.channel_id, channel.state["nonce"], amount]
        )
        signature = bytes(self.sdk.web3.eth.account.signHash(defunct_hash_message(message), self.sdk.account.signer_private_key).signature)
        metadata = [
            ("snet-payment-type", "escrow"),
            ("snet-payment-channel-id", str(channel.channel_id)),
            ("snet-payment-channel-nonce", str(channel.state["nonce"])),
            ("snet-payment-channel-amount", str(amount)),
            ("snet-payment-channel-signature-bin", signature)
        ]
        return metadata


    def _intercept_call(self, client_call_details, request_iterator, request_streaming,
                       response_streaming):
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        metadata.extend(self._get_service_call_metadata())
        client_call_details = _ClientCallDetails(
            client_call_details.method, client_call_details.timeout, metadata,
            client_call_details.credentials)
        return client_call_details, request_iterator, None


    def load_open_channels(self):
        current_block_number = self.sdk.web3.eth.getBlock("latest").number
        new_payment_channels = self.sdk.mpe_contract.get_past_open_channels(self.sdk.account, self, self.last_read_block)
        self.payment_channels = self.payment_channels + new_payment_channels
        self.last_read_block = current_block_number
        return self.payment_channels


    def update_channel_states(self):
        for channel in self.payment_channels:
            channel.sync_state()
        return self.payment_channels


    def default_channel_expiration(self):
        current_block_number = self.sdk.web3.eth.getBlock("latest").number
        return current_block_number + self.expiry_threshold


    def _generate_payment_channel_state_service_client(self):
        grpc_channel = self._base_grpc_channel
        with add_to_path(str(RESOURCES_PATH.joinpath("proto"))):
            state_service_pb2_grpc = importlib.import_module("state_service_pb2_grpc")
        return state_service_pb2_grpc.PaymentChannelStateServiceStub(grpc_channel)


    def open_channel(self, amount, expiration):
        receipt = self.sdk.mpe_contract.open_channel(self.sdk.account, self, amount, expiration)
        return self._get_newly_opened_channel(receipt)


    def deposit_and_open_channel(self, amount, expiration):
        receipt = self.sdk.mpe_contract.deposit_and_open_channel(self.sdk.account, self, amount, expiration)
        return self._get_newly_opened_channel(receipt)


    def _get_newly_opened_channel(self, receipt):
        open_channels = self.sdk.mpe_contract.get_past_open_channels(self.sdk.account, self, receipt["blockNumber"], receipt["blockNumber"])
        return open_channels[0]
