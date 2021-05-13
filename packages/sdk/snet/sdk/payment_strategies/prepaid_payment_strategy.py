from snet.sdk.payment_strategies.payment_staregy import PaymentStrategy


class PrePaidPaymentStrategy(PaymentStrategy):

    def __init__(self, concurrency_manager, block_offset=240, call_allowance=1):
        self.concurrency_manager = concurrency_manager
        self.block_offset = block_offset
        self.call_allowance = call_allowance

    def get_price(self, service_client):
        return service_client.get_price() * self.concurrency_manager.concurrent_calls

    def get_payment_metadata(self, service_client, channel):
        if channel is None:
            channel = self.select_channel(service_client)
        token = self.concurrency_manager.get_token(service_client, channel, self.get_price(service_client))
        metadata = [
            ("snet-payment-type", "prepaid-call"),
            ("snet-payment-channel-id", str(channel.channel_id)),
            ("snet-payment-channel-nonce", str(channel.state["nonce"])),
            ("snet-prepaid-auth-token-bin", bytes(token, 'UTF-8'))
        ]
        return metadata

    def get_concurrency_token_and_channel(self, service_client):
        channel = self.select_channel(service_client)
        token = self.concurrency_manager.get_token(service_client, channel, self.get_price(service_client))
        return token, channel

    def select_channel(self, service_client):
        account = service_client.account
        service_client.load_open_channels()
        service_client.update_channel_states()
        payment_channels = service_client.payment_channels
        service_call_price = self.get_price(service_client)
        extend_channel_fund = service_call_price * self.call_allowance
        mpe_balance = account.escrow_balance()
        default_expiration = service_client.default_channel_expiration()

        if len(payment_channels) < 1:
            if service_call_price > mpe_balance:
                payment_channel = service_client.deposit_and_open_channel(service_call_price,
                                                                          default_expiration + self.block_offset)
            else:
                payment_channel = service_client.open_channel(service_call_price,
                                                              default_expiration + self.block_offset)
        else:
            payment_channel = payment_channels[0]

        if self.__has_sufficient_funds(payment_channel, service_call_price) \
                and not self.__is_valid(payment_channel, default_expiration):
            payment_channel.extend_expiration(default_expiration + self.block_offset)

        elif not self.__has_sufficient_funds(payment_channel, service_call_price) and \
                self.__is_valid(payment_channel, default_expiration):
            payment_channel.add_funds(extend_channel_fund)

        elif not self.__has_sufficient_funds(payment_channel, service_call_price) and \
                not self.__is_valid(payment_channel, default_expiration):
            payment_channel.extend_and_add_funds(default_expiration + self.block_offset, extend_channel_fund)

        return payment_channel

    @staticmethod
    def __has_sufficient_funds(channel, amount):
        return channel.state["available_amount"] >= amount

    @staticmethod
    def __is_valid(channel, expiry):
        return channel.state["expiration"] >= expiry
