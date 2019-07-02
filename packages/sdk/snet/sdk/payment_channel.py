import web3
import importlib
from eth_account.messages import defunct_hash_message

from snet.snet_cli.utils import RESOURCES_PATH, add_to_path

class PaymentChannel:
    def __init__(self, channel_id, w3, account, service, mpe_contract):
        self.channel_id = channel_id
        self.web3 = w3
        self.account = account
        self.mpe_contract = mpe_contract
        self.payment_channel_state_service_client = service.payment_channel_state_service_client
        self.state = {
            "nonce": 0,
            "last_signed_amount": 0
        }


    def add_funds(self, amount):
        return self.mpe_contract.channel_add_funds(self.account, self.channel_id, amount)


    def extend_expiration(self, expiration):
        return self.mpe_contract.channel_extend(self.account, self.channel_id, expiration)


    def extend_and_add_funds(self, expiration, amount):
        return self.mpe_contract.channel_extend_and_add_funds(self.account, self.channel_id, expiration, amount)


    def sync_state(self):
        channel_blockchain_data = self.mpe_contract.contract.functions.channels(self.channel_id).call()
        (current_nonce, last_signed_amount) = self._get_current_channel_state()
        nonce = channel_blockchain_data[0]
        total_amount = channel_blockchain_data[5]
        expiration = channel_blockchain_data[6]
        available_amount = total_amount - last_signed_amount
        self.state = {
            "current_nonce": current_nonce,
            "last_signed_amount": last_signed_amount,
            "nonce": nonce,
            "total_amount": total_amount,
            "expiration": expiration,
            "available_amount": available_amount
        }


    def _get_current_channel_state(self):
        stub = self.payment_channel_state_service_client
        message = web3.Web3.soliditySha3(["uint256"], [self.channel_id])
        signature = self.web3.eth.account.signHash(defunct_hash_message(message), self.account.signer_private_key).signature
        with add_to_path(str(RESOURCES_PATH.joinpath("proto"))):
            state_service_pb2 = importlib.import_module("state_service_pb2")
        request = state_service_pb2.ChannelStateRequest(channel_id=web3.Web3.toBytes(self.channel_id), signature=bytes(signature))
        response = stub.GetChannelState(request)
        return int.from_bytes(response.current_nonce, byteorder="big"), int.from_bytes(response.current_signed_amount, byteorder="big")
