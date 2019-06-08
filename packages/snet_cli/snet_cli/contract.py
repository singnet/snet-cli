class Contract:
    def __init__(self, w3, address, abi):
        self.w3 = w3
        self.contract = self.w3.eth.contract(address=self.w3.toChecksumAddress(address), abi=abi)
        self.abi = abi

    def call(self, function_name, *positional_inputs, **named_inputs):
        return getattr(self.contract.functions, function_name)(*positional_inputs, **named_inputs).call()

    def build_transaction(self, function_name, from_address, gas_price, *positional_inputs, **named_inputs):
        nonce = self.w3.eth.getTransactionCount(from_address)
        chain_id = self.w3.version.network
        return getattr(self.contract.functions, function_name)(*positional_inputs, **named_inputs).buildTransaction({
            "from": from_address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "chainId": int(chain_id)
        })

    def process_receipt(self, receipt):
        events = []

        contract_events = map(lambda e: e["name"], filter(lambda e: e["type"] == "event", self.abi))
        for contract_event in contract_events:
            events.extend(getattr(self.contract.events, contract_event)().processReceipt(receipt))

        return events
