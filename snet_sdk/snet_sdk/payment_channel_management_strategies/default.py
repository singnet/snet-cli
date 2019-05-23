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
        service_call_price = service_client.metadata.pricing["price_in_cogs"]
        mpe_balance = account.escrow_balance()
        default_expiration = service_client.default_channel_expiration()

        if len(payment_channels) == 0:
            if mpe_balance > service_call_price*self.call_allowance:
                return service_client.open_channel(service_call_price*self.call_allowance, default_expiration + self.block_offset)
            return service_client.deposit_and_open_channel(service_call_price*self.call_allowance - mpe_balance, default_expiration + self.block_offset)

        funded_valid_channels = [channel for channel in payment_channels if self._has_sufficient_funds(channel, service_call_price) and self._is_valid(channel, default_expiration)]
        if len(funded_valid_channels):
            return funded_valid_channels[0]
        
        funded_channels = [channel for channel in payment_channels if self._has_sufficient_funds(channel, service_call_price)]
        if len(funded_channels):
            funded_channels[0].extend_expiration(default_expiration + self.block_offset)
            return funded_channels[0]

        valid_channels = [channel for channel in payment_channels if self._is_valid(channel, default_expiration)]
        if len(valid_channels):
            valid_channels[0].add_funds(service_call_price*self.call_allowance)
            return valid_channels[0]

        first_expired_and_unfunded_channel = payment_channels[0]
        first_expired_and_unfunded_channel.extend_and_add_funds(default_expiration + self.block_offset, service_call_price*self.call_allowance)
        return first_expired_and_unfunded_channel


    @staticmethod
    def _has_sufficient_funds(channel, amount):
        return channel.state["available_amount"] >= amount


    @staticmethod
    def _is_valid(channel, expiry):
        return channel.state["expiration"] >= expiry
