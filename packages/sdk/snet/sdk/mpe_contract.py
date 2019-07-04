import base64

import web3
from snet.sdk.payment_channel import PaymentChannel

from snet.snet_cli.utils import get_contract_object, get_contract_deployment_block


BLOCKS_PER_BATCH = 20000


class MPEContract:
    def __init__(self, w3):
        self.web3 = w3
        self.contract = get_contract_object(self.web3, "MultiPartyEscrow.json")
        self.event_topics = [self.web3.sha3(text="ChannelOpen(uint256,uint256,address,address,address,bytes32,uint256,uint256)").hex()]
        self.deployment_block = get_contract_deployment_block(self.web3, "MultiPartyEscrow.json")


    def get_past_open_channels(self, account, service, starting_block_number=0, to_block_number=None):
        if to_block_number is None:
            to_block_number = self.web3.eth.getBlock("latest")["number"]

        if starting_block_number == 0:
            starting_block_number = self.deployment_block

        logs = []
        from_block = starting_block_number
        while from_block <= to_block_number:
            to_block = min(from_block + BLOCKS_PER_BATCH, to_block_number)
            logs = logs + self.web3.eth.getLogs({"fromBlock" : from_block, "toBlock": to_block, "address": self.contract.address, "topics": self.event_topics})
            from_block = to_block + 1

        event_abi = self.contract._find_matching_event_abi(event_name="ChannelOpen")
        group = service.metadata.get_group_id(service.group['group_name'])
        channels_opened = list(filter(
            lambda channel: channel.sender == account.address and channel.signer == account.signer_address and channel.recipient == service.group["payment_address"] and channel.groupId == group,
            [web3.utils.events.get_event_data(event_abi, l)["args"] for l in logs]
        ))
        return list(map(lambda channel: PaymentChannel(channel["channelId"], self.web3, account, service, self), channels_opened))


    def balance(self, address):
        return self.contract.functions.balances(address).call()


    def deposit(self, account, amount_in_cogs):
        return account.send_transaction(self.contract.functions.deposit, amount_in_cogs)


    def open_channel(self, account, service, amount, expiration):
        return account.send_transaction(self.contract.functions.openChannel, account.signer_address, service.group["payment_address"], base64.b64decode(str(service.group["group_id"])), amount, expiration)


    def deposit_and_open_channel(self, account, service, amount, expiration):
        already_approved_amount = account.allowance()
        if amount > already_approved_amount:
            account.approve_transfer(amount)
        return account.send_transaction(self.contract.functions.depositAndOpenChannel, account.signer_address, service.group["payment_address"], base64.b64decode(str(service.group["group_id"])), amount, expiration)


    def channel_add_funds(self, account, channel_id, amount):
        self._fund_escrow_account(account, amount)
        return account.send_transaction(self.contract.functions.channelAddFunds, channel_id, amount)


    def channel_extend(self, account, channel_id, expiration):
        return account.send_transaction(self.contract.functions.channelExtend, channel_id, expiration)


    def channel_extend_and_add_funds(self, account, channel_id, expiration, amount):
        self._fund_escrow_account(account, amount)
        return account.send_transaction(self.contract.functions.channelExtendAndAddFunds, channel_id, expiration, amount)

    def _fund_escrow_account(self, account, amount):
        current_escrow_balance = self.balance(account.address)
        if amount > current_escrow_balance:
            account.deposit_to_escrow_account(amount - current_escrow_balance)
