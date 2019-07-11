class PaymentChannelManagementStrategy:
    def __init__(self, sdk_context, block_offset=0, call_allowance=1):
        self.sdk_context = sdk_context
        self.block_offset = block_offset
        self.call_allowance = call_allowance

    def select_channel(self, service_client):
        account = self.sdk_context.account
        service_client.load_open_channels()
        service_client.update_channel_states()
        payment_channels = service_client.payment_channels
        service_call_price = service_client.metadata["pricing"]["price_in_cogs"]
        mpe_balance = account.escrow_balance()
        default_expiration = service_client.default_channel_expiration()

        payment_channel = payment_channels[0]

        if self._has_sufficient_funds(payment_channel, service_call_price) and not self._is_valid(payment_channel, default_expiration):
            payment_channel.extend_expiration(default_expiration + self.block_offset)
        elif not self._has_sufficient_funds(payment_channel, service_call_price) and self._is_valid(payment_channel, default_expiration):
            payment_channel.add_funds(service_call_price*self.call_allowance)
        elif not self._has_sufficient_funds(payment_channel, service_call_price) and not self._is_valid(payment_channel, default_expiration):
            payment_channel.extend_and_add_funds(default_expiration + self.block_offset, service_call_price*self.call_allowance)

        return payment_channel


    @staticmethod
    def _has_sufficient_funds(channel, amount):
        return channel.state["available_amount"] >= amount


    @staticmethod
    def _is_valid(channel, expiry):
        return channel.state["expiration"] >= expiry
