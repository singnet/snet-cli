from snet_cli.mpe_channel_command import MPEChannelCommand
from snet_cli.utils import compile_proto
import base64
from pathlib import Path
import json
import sys
import grpc
from eth_account.messages import defunct_hash_message
from snet_cli.utils_proto import import_protobuf_from_dir, switch_to_json_payload_encoding
from snet_cli.utils_agi2cogs import cogs2stragi
from snet_cli.utils import remove_http_https_prefix


# we inherit MPEChannelCommand because client needs channels
class MPEClientCommand(MPEChannelCommand):

    # I. Signature related functions
    def _compose_message_to_sign(self, mpe_address, channel_id, nonce, amount):
        return self.w3.soliditySha3(
               ["address",   "uint256", "uint256", "uint256"],
               [mpe_address, channel_id, nonce,     amount])

    def _sign_message(self, mpe_address, channel_id, nonce, amount):
        message = self._compose_message_to_sign(mpe_address, channel_id, nonce, amount)
        sign    = self.ident.sign_message_after_soliditySha3(message)
        return sign

    def _verify_my_signature(self, signature, mpe_address, channel_id, nonce, amount):
        message      = self._compose_message_to_sign(mpe_address, channel_id, nonce, amount)
        message_hash = defunct_hash_message(message)
        sign_address = self.ident.w3.eth.account.recoverHash(message_hash, signature=signature)
        return sign_address == self.ident.address

    # II. Call related functions (low level)

    def _get_call_params(self):
        params_string = self.args.params

        # try to read from command line
        if params_string is None or params_string == "-":
            self._printerr("Waiting for call params on stdin...")
            params_string = sys.stdin.read()

        # If it is a file, try to read from it
        if Path(params_string).is_file():
            self._printerr("Read call params from the file: %s"%params_string)
            with open(params_string, 'rb') as f:
                params_string = f.read()

        try:
            params = json.loads(params_string)
        except ValueError:
            self._printerr('Decoding JSON has failed (parameters should be in JSON format)')
            raise

        try:
            params = self._transform_call_params(params)
        except Exception as e:
            self._printerr('Fail to "transform" call params')
            raise

        return params


    def _transform_call_params(self, params):
        """
        possible modifiers: file, b64encode, b64decode
        format:             modifier1@modifier2@...modifierN@k_final
        """
        rez = {}
        for k, v in params.items():
            if isinstance(v, dict):
                v = self._transform_call_params(v)
                k_final = k
            else:
                # k = modifier1@modifier2@...modifierN@k_final
                k_split = k.split("@")
                k_final = k_split[-1]
                k_mods  = k_split[:-1]
                for m in k_mods:
                    if (m == "file"):
                        with open(v, 'rb') as f:
                            v = f.read()
                    elif (m == "b64encode"):
                        v = base64.b64encode(v)
                    elif (m == "b64decode"):
                        v = base64.b64decode(v)
                    else:
                        raise Exception("Unknown modifier ('%s') in call parameters. Possible modifiers: file, b64encode, b64decode"%m)
            rez[k_final] = v
        return rez

    def _import_protobuf_for_service(self):
        spec_dir = self.get_service_spec_dir(self.args.org_id, self.args.service_id)
        return import_protobuf_from_dir(spec_dir, self.args.method, self.args.service)

    def _call_server_via_grpc_channel(self, grpc_channel, channel_id, nonce, amount, params, service_metadata):
        stub_class, request_class, response_class = self._import_protobuf_for_service()

        request  = request_class(**params)
        stub     = stub_class(grpc_channel)
        call_fn  = getattr(stub, self.args.method)

        if service_metadata["encoding"] == "json":
            switch_to_json_payload_encoding(call_fn, response_class)

        mpe_address = self.get_mpe_address()
        signature = self._sign_message(mpe_address, channel_id, nonce, amount)
        metadata = [("snet-payment-type",                 "escrow"                    ),
                    ("snet-payment-channel-id",            str(channel_id)  ),
                    ("snet-payment-channel-nonce",         str(nonce)       ),
                    ("snet-payment-channel-amount",        str(amount)      ),
                    ("snet-payment-channel-signature-bin", bytes(signature))]
        return call_fn(request, metadata=metadata)

    def _deal_with_call_response(self, response):
        if (self.args.save_response):
            with open(self.args.save_response, "wb") as f:
                f.write(response.SerializeToString())
        elif (self.args.save_field):
            field = getattr(response, self.args.save_field[0])
            file_name = self.args.save_field[1]
            if (type(field) == bytes):
                with open(file_name, "wb") as f:
                    f.write(field)
            else:
                with open(file_name, "w") as f:
                    f.write(str(field))
        else:
            self._printout(response)

    def _open_grpc_channel(self, endpoint):
        """
           open grpc channel:
               - for http://  we open insecure_channel
               - for https:// we open secure_channel (with default credentials)
               - without prefix we open insecure_channel
        """
        if (endpoint.startswith("https://")):
            return grpc.secure_channel(remove_http_https_prefix(endpoint), grpc.ssl_channel_credentials())
        return grpc.insecure_channel(remove_http_https_prefix(endpoint))

    def _get_endpoint_from_metadata_or_args(self, metadata):
        if (self.args.endpoint):
            return self.args.endpoint
        endpoints = metadata.get_endpoints_for_group(self.args.group_name)
        if (not endpoints):
            raise Exception("Cannot find endpoint in metadata for the given payment group.")
        if (len(endpoints) > 1):
            self._printerr("There are several endpoints for the given payment group. We will select %s"%endpoints[0])
        return endpoints[0]

    def call_server_lowlevel(self):
        params           = self._get_call_params()
        service_metadata = self._read_metadata_for_service(self.args.org_id, self.args.service_id)
        endpoint         = self._get_endpoint_from_metadata_or_args(service_metadata)
        grpc_channel     = self._open_grpc_channel(endpoint)

        response = self._call_server_via_grpc_channel(grpc_channel, self.args.channel_id, self.args.nonce, self.args.amount_in_cogs, params, service_metadata)
        self._deal_with_call_response(response)

    # III. Stateless client related functions
    def _get_channel_state_from_server(self, grpc_channel, channel_id):
        # Compile protobuf if needed
        codegen_dir = Path.home().joinpath(".snet", "mpe_client", "state_service")
        proto_dir   = Path(__file__).absolute().parent.joinpath("resources", "proto")
        if (not codegen_dir.joinpath("state_service_pb2.py").is_file()):
            compile_proto(proto_dir, codegen_dir, proto_file = "state_service.proto")

        # make PaymentChannelStateService.GetChannelState call to the daemon
        stub_class, request_class, _ = import_protobuf_from_dir(codegen_dir, "GetChannelState")
        message   = self.w3.soliditySha3(["uint256"], [channel_id])
        signature = self.ident.sign_message_after_soliditySha3(message)

        request   = request_class(channel_id = self.w3.toBytes(channel_id), signature = bytes(signature))

        stub     = stub_class(grpc_channel)
        response = getattr(stub, "GetChannelState")(request)
        # convert bytes to int
        state = dict()
        state["current_nonce"]          = int.from_bytes(response.current_nonce,         byteorder='big')
        state["current_signed_amount"]  = int.from_bytes(response.current_signed_amount, byteorder='big')
        if (state["current_signed_amount"] > 0):
         good = self._verify_my_signature(bytes(response.current_signature), self.get_mpe_address(), channel_id, state["current_nonce"], state["current_signed_amount"])
         if (not good):
             raise Exception("Error in _get_channel_state_from_server. My own signature from the server is not valid.")

        return state

    def _get_channel_state_statelessly(self, grpc_channel, channel_id):
        """
        We get state of the channel (nonce, amount, unspent_amount)
        We do it by securely combine information from the server and blockchain
        https://github.com/singnet/wiki/blob/master/multiPartyEscrowContract/MultiPartyEscrow_stateless_client.md
        """
        server     = self._get_channel_state_from_server    (grpc_channel, channel_id)
        blockchain = self._get_channel_state_from_blockchain(              channel_id)

        if (server["current_nonce"] == blockchain["nonce"]):
            unspent_amount = blockchain["value"] - server["current_signed_amount"]
        else:
            unspent_amount = None # in this case we cannot securely define unspent_amount yet

        return (server["current_nonce"], server["current_signed_amount"], unspent_amount)

    def print_channel_state_statelessly(self):
        grpc_channel     = self._open_grpc_channel(self.args.endpoint)

        current_nonce, current_amount, unspent_amount = self._get_channel_state_statelessly(grpc_channel, self.args.channel_id)
        self._printout("current_nonce                  = %i"%current_nonce)
        self._printout("current_signed_amount_in_cogs  = %i"%current_amount)
        self._printout("current_unspent_amount_in_cogs = %s"%str(unspent_amount))

    def _get_price_from_metadata(self, service_metadata):
        pricing = service_metadata["pricing"]
        if (pricing["price_model"] == "fixed_price"):
            return pricing["price_in_cogs"]
        raise Exception("We do not support price model: %s"%(pricing["price_model"]))

    def call_server_statelessly_with_params(self, params):

        # if service is not initilized we will initialize it (unless we want skip registry check for update)
        if (not self.args.skip_update_check):
            self._init_or_update_registered_service_if_needed()

        service_metadata = self._read_metadata_for_service(self.args.org_id, self.args.service_id)
        endpoint         = self._get_endpoint_from_metadata_or_args(service_metadata)
        grpc_channel     = self._open_grpc_channel(endpoint)

        # if channel was not initilized we will try to initailize it (it will work only in simple case of signer == sender)
        channel       = self._smart_get_initialized_channel_for_service(service_metadata, filter_by = "signer")
        channel_id    = channel["channelId"]
        price         = self._get_price_from_metadata(service_metadata)
        server_state  = self._get_channel_state_from_server(grpc_channel, channel_id)

        proceed = self.args.yes or input("Price for this call will be %s AGI (use -y to remove this warning). Proceed? (y/n): "%(cogs2stragi(price))) == "y"
        if (not proceed):
            self._error("Cancelled")

        return self._call_server_via_grpc_channel(grpc_channel, channel_id, server_state["current_nonce"], server_state["current_signed_amount"] + price, params, service_metadata)

    def call_server_statelessly(self):
        params           = self._get_call_params()
        response = self.call_server_statelessly_with_params(params)
        self._deal_with_call_response(response)
