from snet.sdk.concurrency_manager import ConcurrencyManager
from snet.sdk.payment_strategies.paidcall_payment_strategy import PaidCallPaymentStrategy
from snet.sdk.payment_strategies.freecall_payment_strategy import FreeCallPaymentStrategy
from snet.sdk.payment_strategies.payment_staregy import PaymentStrategy
from snet.sdk.payment_strategies.prepaid_payment_strategy import PrePaidPaymentStrategy


class DefaultPaymentStrategy(PaymentStrategy):

    def __init__(self, concurrent_calls=1):
        self.concurrent_calls = concurrent_calls
        self.concurrencyManager = ConcurrencyManager(concurrent_calls)
        self.channel = None

    def set_concurrency_token(self, token):
        self.concurrencyManager.__token = token

    def set_channel(self, channel):
        self.channel = channel

    def get_payment_metadata(self, service_client):
        free_call_payment_strategy = FreeCallPaymentStrategy()

        if free_call_payment_strategy.is_free_call_available(service_client):
            metadata = free_call_payment_strategy.get_payment_metadata(service_client)
        else:
            if service_client.get_concurrency_flag():
                payment_strategy = PrePaidPaymentStrategy(self.concurrencyManager)
                metadata = payment_strategy.get_payment_metadata(service_client, self.channel)
            else:
                payment_strategy = PaidCallPaymentStrategy()
                metadata = payment_strategy.get_payment_metadata(service_client)

        return metadata

    def get_price(self, service_client):
        pass

    def get_concurrency_token_and_channel(self, service_client):
        payment_strategy = PrePaidPaymentStrategy(self.concurrencyManager)
        return payment_strategy.get_concurrency_token_and_channel(service_client)

