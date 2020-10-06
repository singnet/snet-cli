from snet_cli.commands.commands import BlockchainCommand
from snet_cli.utils.agi2cogs import cogs2stragi


class MPEAccountCommand(BlockchainCommand):

    def print_account(self):
        self._printout(self.ident.address)

    def print_agi_and_mpe_balances(self):
        """ Print balance of ETH, AGI, and MPE wallet """
        if (self.args.account):
            account = self.args.account
        else:
            account = self.ident.address
        eth_wei  = self.w3.eth.getBalance(account)
        agi_cogs = self.call_contract_command("SingularityNetToken", "balanceOf", [account])
        mpe_cogs = self.call_contract_command("MultiPartyEscrow",    "balances",  [account])

        # we cannot use _pprint here because it doesn't conserve order yet
        self._printout("    account: %s"%account)
        self._printout("    ETH: %s"%self.w3.fromWei(eth_wei, 'ether'))
        self._printout("    AGI: %s"%cogs2stragi(agi_cogs))
        self._printout("    MPE: %s"%cogs2stragi(mpe_cogs))

    def deposit_to_mpe(self):
        amount      = self.args.amount
        mpe_address = self.get_mpe_address()

        already_approved = self.call_contract_command("SingularityNetToken", "allowance", [self.ident.address, mpe_address])
        if (already_approved < amount):
            self.transact_contract_command("SingularityNetToken", "approve", [mpe_address, amount])
        self.transact_contract_command("MultiPartyEscrow", "deposit", [amount])

    def withdraw_from_mpe(self):
        self.transact_contract_command("MultiPartyEscrow", "withdraw", [self.args.amount])

    def transfer_in_mpe(self):
        self.transact_contract_command("MultiPartyEscrow", "transfer", [self.args.receiver, self.args.amount])
