from snet.sdk.payment_strategies.default import PaymentChannelManagementStrategy
from snet.sdk.payment_strategies.payment_staregy import PaymentStrategy


class FreeCallPaymentStrategy(PaymentStrategy):

    def is_free_call_available(self):
        #TODO get free call from daemon
        return False

    def get_payment_metadata(self, service_client):

        if self.is_free_call_available():
            #TODO integration test with daemon for free call
            metadata = []
        else:
            payment_strategy = PaymentChannelManagementStrategy()
            metadata = payment_strategy.get_payment_metadata(service_client)

        return metadata

    def select_channel(self,service_client):
        pass

