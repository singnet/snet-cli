import web3
from snet.sdk.mpe.mpe_contract import MPEContract

from snet.sdk.mpe.payment_channel import PaymentChannel
from snet.snet_cli.utils.utils import get_contract_deployment_block

BLOCKS_PER_BATCH = 20000


class PaymentChannelProvider(object):

    def __init__(self, w3, payment_channel_state_service_client, mpe_contract):
        self.web3 = w3

        self.mpe_contract = mpe_contract
        self.event_topics = [self.web3.sha3(
            text="ChannelOpen(uint256,uint256,address,address,address,bytes32,uint256,uint256)").hex()]
        self.deployment_block = get_contract_deployment_block(
            self.web3, "MultiPartyEscrow.json")
        self.payment_channel_state_service_client = payment_channel_state_service_client

    def get_past_open_channels(self, account, payment_address, group_id, starting_block_number=0, to_block_number=None):
        if to_block_number is None:
            to_block_number = self.web3.eth.getBlock("latest")["number"]

        if starting_block_number == 0:
            starting_block_number = self.deployment_block

        logs = []
        from_block = starting_block_number
        while from_block <= to_block_number:
            to_block = min(from_block + BLOCKS_PER_BATCH, to_block_number)
            logs = logs + self.web3.eth.getLogs({"fromBlock": from_block, "toBlock": to_block,
                                                 "address": self.mpe_contract.contract.address,
                                                 "topics": self.event_topics})
            from_block = to_block + 1

        event_abi = self.mpe_contract.contract._find_matching_event_abi(
            event_name="ChannelOpen")

        channels_opened = list(filter(
            lambda
                channel: channel.sender == account.address and channel.signer == account.signer_address and channel.recipient ==
                         payment_address and channel.groupId == group_id,
            [web3.utils.events.get_event_data(
                event_abi, l)["args"] for l in logs]
        ))
        return list(map(lambda channel: PaymentChannel(channel["channelId"], self.web3, account,
                                                       self.payment_channel_state_service_client, self.mpe_contract),
                        channels_opened))

    def open_channel(self, account, amount, expiration, payment_address, group_id):

        receipt = self.mpe_contract.open_channel(account, payment_address, group_id, amount, expiration)
        return self._get_newly_opened_channel(receipt, account, payment_address, group_id)

    def deposit_and_open_channel(self, account, amount, expiration, payment_address, group_id):
        receipt = self.mpe_contract.deposit_and_open_channel(account, payment_address, group_id, amount,
                                                             expiration)
        return self._get_newly_opened_channel(receipt, account, payment_address, group_id)

    def _get_newly_opened_channel(self, receipt,account, payment_address, group_id):
        open_channels = self.get_past_open_channels(account, payment_address, group_id, receipt["blockNumber"],
                                                    receipt["blockNumber"])
        if len(open_channels) == 0:
            raise Exception(f"Error while opening channel, please check transaction {receipt.transactionHash.hex()} ")
        return open_channels[0]
