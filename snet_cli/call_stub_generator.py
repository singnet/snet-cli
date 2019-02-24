from snet_cli.mpe_client_command import MPEClientCommand
from snet_cli.config import Config
from snet_cli.utils import DefaultAttributeObject

def call_stub_generator(org_id, service_id, method, **kwargs):
    conf = Config()
    args = DefaultAttributeObject(org_id = org_id, service_id = service_id, method = method, yes = True, **kwargs)
    class Stub:
        def __call__(self, params):
            return self.client.call_server_statelessly_with_params(params)
    stub = Stub()
    stub.client = MPEClientCommand(conf, args)
    return stub
