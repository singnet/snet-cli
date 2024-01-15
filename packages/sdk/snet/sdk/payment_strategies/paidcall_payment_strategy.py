import web3
from snet.sdk.payment_strategies.payment_staregy import PaymentStrategy


class PaidCallPaymentStrategy(PaymentStrategy):
    def __init__(self, block_offset=240, call_allowance=1):
        self.block_offset = block_offset
        self.call_allowance = call_allowance

    def get_price(self, service_client):
        return service_client.get_price()

    def get_payment_metadata(self, service_client):
        channel = self.select_channel(service_client)
        amount = channel.state["last_signed_amount"] + int(self.get_price(service_client))
        message = web3.Web3.solidity_keccak(
            ["string", "address", "uint256", "uint256", "uint256"],
            ["__MPE_claim_message", service_client.mpe_address, channel.channel_id,
             channel.state["nonce"],
             amount]
        )
        signature = service_client.generate_signature(message)

        metadata = [
            ("snet-payment-type", "escrow"),
            ("snet-payment-channel-id", str(channel.channel_id)),
            ("snet-payment-channel-nonce", str(channel.state["nonce"])),
            ("snet-payment-channel-amount", str(amount)),
            ("snet-payment-channel-signature-bin", signature)
        ]

        return metadata

    def select_channel(self, service_client):
        account = service_client.account
        service_client.load_open_channels()
        service_client.update_channel_states()
        payment_channels = service_client.payment_channels
        # picking the first pricing strategy as default for now
        service_call_price = self.get_price(service_client)
        mpe_balance = account.escrow_balance()
        default_expiration = service_client.default_channel_expiration()

        if len(payment_channels) < 1:
            if service_call_price > mpe_balance:
                payment_channel = service_client.deposit_and_open_channel(service_call_price,
                                                                          default_expiration + self.block_offset)
            else:
                payment_channel = service_client.open_channel(service_call_price,
                                                              default_expiration + self.block_offset)
            service_client.payment_channels = service_client.payment_channels + [payment_channel]
            service_client.update_channel_states()
        else:
            payment_channel = payment_channels[0]

        if self._has_sufficient_funds(payment_channel, service_call_price) and not self._is_valid(payment_channel,
                                                                                                  default_expiration):
            payment_channel.extend_expiration(default_expiration + self.block_offset)
        elif not self._has_sufficient_funds(payment_channel, service_call_price) and self._is_valid(payment_channel,
                                                                                                    default_expiration):
            payment_channel.add_funds(service_call_price * self.call_allowance)
        elif not self._has_sufficient_funds(payment_channel, service_call_price) and not self._is_valid(payment_channel,
                                                                                                        default_expiration):
            payment_channel.extend_and_add_funds(default_expiration + self.block_offset,
                                                 service_call_price * self.call_allowance)

        return payment_channel

    @staticmethod
    def _has_sufficient_funds(channel, amount):
        return channel.state["available_amount"] >= amount

    @staticmethod
    def _is_valid(channel, expiry):
        return channel.state["expiration"] >= expiry
