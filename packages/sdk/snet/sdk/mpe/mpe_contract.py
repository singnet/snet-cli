from snet.snet_cli.utils.utils import get_contract_deployment_block, get_contract_object



class MPEContract:
    def __init__(self, w3, address=None):
        self.web3 = w3
        if address is None:
            self.contract = get_contract_object(self.web3, "MultiPartyEscrow.json")
        else:
            self.contract = get_contract_object(self.web3, "MultiPartyEscrow.json", address)
        self.event_topics = [self.web3.sha3(
            text="ChannelOpen(uint256,uint256,address,address,address,bytes32,uint256,uint256)").hex()]
        self.deployment_block = get_contract_deployment_block(
            self.web3, "MultiPartyEscrow.json")


    def balance(self, address):
        return self.contract.functions.balances(address).call()

    def deposit(self, account, amount_in_cogs):
        return account.send_transaction(self.contract.functions.deposit, amount_in_cogs)

    def open_channel(self, account, payment_address, group_id, amount, expiration):
        return account.send_transaction(self.contract.functions.openChannel, account.signer_address, payment_address,
                                        group_id, amount, expiration)

    def deposit_and_open_channel(self, account, payment_address, group_id, amount, expiration):
        already_approved_amount = account.allowance()
        if amount > already_approved_amount:
            account.approve_transfer(amount)
        return account.send_transaction(self.contract.functions.depositAndOpenChannel, account.signer_address,
                                        payment_address, group_id, amount, expiration)

    def channel_add_funds(self, account, channel_id, amount):
        self._fund_escrow_account(account, amount)
        return account.send_transaction(self.contract.functions.channelAddFunds, channel_id, amount)

    def channel_extend(self, account, channel_id, expiration):
        return account.send_transaction(self.contract.functions.channelExtend, channel_id, expiration)

    def channel_extend_and_add_funds(self, account, channel_id, expiration, amount):
        self._fund_escrow_account(account, amount)
        return account.send_transaction(self.contract.functions.channelExtendAndAddFunds, channel_id, expiration,
                                        amount)

    def _fund_escrow_account(self, account, amount):
        current_escrow_balance = self.balance(account.address)
        if amount > current_escrow_balance:
            account.deposit_to_escrow_account(amount - current_escrow_balance)
