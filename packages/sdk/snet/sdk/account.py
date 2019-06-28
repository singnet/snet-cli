import json

from snet.snet_cli.utils import normalize_private_key, get_address_from_private, get_contract_object

DEFAULT_GAS = 210000


class TransactionError(Exception):
    """Raised when an Ethereum transaction receipt has a status of 0. Can provide a custom message. Optionally includes receipt"""

    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.message = message
        self.receipt = receipt

    def __str__(self):
        return self.message


class Account:
    def __init__(self, w3, config, mpe_contract):
        self.config = config
        self.web3 = w3
        self.mpe_contract = mpe_contract
        self.token_contract = get_contract_object(
            self.web3, "SingularityNetToken.json")
        private_key = config.get("private_key", None)
        signer_private_key = config.get("signer_private_key", None)
        if private_key is not None:
            self.private_key = normalize_private_key(config["private_key"])
        if signer_private_key is not None:
            self.signer_private_key = normalize_private_key(
                config["signer_private_key"])
        else:
            self.signer_private_key = self.private_key
        self.address = get_address_from_private(self.private_key)
        self.signer_address = get_address_from_private(self.signer_private_key)
        self.nonce = 0

    def _get_nonce(self):
        nonce = self.web3.eth.getTransactionCount(self.address)
        if self.nonce >= nonce:
            nonce = self.nonce + 1
        self.nonce = nonce
        return nonce

    def _get_gas_price(self):
        return int(self.web3.eth.generateGasPrice())

    def _send_signed_transaction(self, contract_fn, *args):
        transaction = contract_fn(*args).buildTransaction({
            "chainId": int(self.web3.version.network),
            "gas": DEFAULT_GAS,
            "gasPrice": self._get_gas_price(),
            "nonce": self._get_nonce()
        })
        signed_txn = self.web3.eth.account.signTransaction(
            transaction, private_key=self.private_key)
        return self.web3.toHex(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction))

    def send_transaction(self, contract_fn, *args):
        txn_hash = self._send_signed_transaction(contract_fn, *args)
        return self.web3.eth.waitForTransactionReceipt(txn_hash, 300)

    def _parse_receipt(self, receipt, event, encoder=json.JSONEncoder):
        if receipt.status == 0:
            raise TransactionError("Transaction failed", receipt)
        else:
            return json.dumps(dict(event().processReceipt(receipt)[0]["args"]), cls=encoder)

    def escrow_balance(self):
        return self.mpe_contract.balance(self.address)

    def deposit_to_escrow_account(self, amount_in_cogs):
        already_approved = self.allowance()
        if amount_in_cogs > already_approved:
            self.approve_transfer(amount_in_cogs)
        return self.mpe_contract.deposit(self, amount_in_cogs)

    def approve_transfer(self, amount_in_cogs):
        return self.send_transaction(self.token_contract.functions.approve(self.mpe_contract.contract.address, amount_in_cogs))

    def allowance(self):
        return self.token_contract.functions.allowance(self.address, self.mpe_contract.contract.address).call()
