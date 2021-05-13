import base64
import json
import sys
from pathlib import Path

from eth_account.messages import defunct_hash_message
from snet.snet_cli.utils.proto_utils import import_protobuf_from_dir, switch_to_json_payload_encoding
from snet.snet_cli.utils.utils import open_grpc_channel, rgetattr, RESOURCES_PATH
from snet_cli.commands.mpe_channel import MPEChannelCommand
from snet_cli.utils.agi2cogs import cogs2stragi


# we inherit MPEChannelCommand because client needs channels
class MPEClientCommand(MPEChannelCommand):
    prefixInSignature = "__MPE_claim_message"

    # I. Signature related functions
    def _compose_message_to_sign(self, mpe_address, channel_id, nonce, amount):
        return self.w3.soliditySha3(
            ["string", "address",   "uint256", "uint256", "uint256"],
            [self.prefixInSignature, mpe_address, channel_id, nonce,     amount])

    def _sign_message(self, mpe_address, channel_id, nonce, amount):
        message = self._compose_message_to_sign(
            mpe_address, channel_id, nonce, amount)
        sign = self.ident.sign_message_after_soliditySha3(message)
        return sign

    def _verify_my_signature(self, signature, mpe_address, channel_id, nonce, amount):
        message = self._compose_message_to_sign(
            mpe_address, channel_id, nonce, amount)
        message_hash = defunct_hash_message(message)
        sign_address = self.ident.w3.eth.account.recoverHash(
            message_hash, signature=signature)
        return sign_address == self.ident.address

    def _assert_validity_of_my_signature_or_zero_amount(self, signature, channel_id, nonce, signed_amount, error_message):
        if (signed_amount > 0):
            if (not self._verify_my_signature(signature, self.get_mpe_address(), channel_id, nonce, signed_amount)):
                raise Exception(error_message)

    # II. Call related functions (low level)

    def _get_call_params(self):
        params_string = self.args.params

        # try to read from command line
        if params_string is None or params_string == "-":
            self._printerr("Waiting for call params on stdin...")
            params_string = sys.stdin.read()

        # If it is a file, try to read from it
        if Path(params_string).is_file():
            self._printerr("Read call params from the file: %s" %
                           params_string)
            with open(params_string, 'rb') as f:
                params_string = f.read()

        try:
            params = json.loads(params_string)
        except ValueError:
            self._printerr(
                'Decoding JSON has failed (parameters should be in JSON format)')
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
                k_mods = k_split[:-1]
                for m in k_mods:
                    if (m == "file"):
                        with open(v, 'rb') as f:
                            v = f.read()
                    elif (m == "b64encode"):
                        v = base64.b64encode(v)
                    elif (m == "b64decode"):
                        v = base64.b64decode(v)
                    else:
                        raise Exception(
                            "Unknown modifier ('%s') in call parameters. Possible modifiers: file, b64encode, b64decode" % m)
            rez[k_final] = v
        return rez

    def _import_protobuf_for_service(self):
        spec_dir = self.get_service_spec_dir(
            self.args.org_id, self.args.service_id)
        return import_protobuf_from_dir(spec_dir, self.args.method, self.args.service)

    def _call_server_via_grpc_channel(self, grpc_channel, channel_id, nonce, amount, params, service_metadata):
        stub_class, request_class, response_class = self._import_protobuf_for_service()

        request = request_class(**params)
        stub = stub_class(grpc_channel)
        call_fn = getattr(stub, self.args.method)

        if service_metadata["encoding"] == "json":
            switch_to_json_payload_encoding(call_fn, response_class)

        metadata = self._create_call_metadata(channel_id, nonce, amount)
        return call_fn(request, metadata=metadata)

    def _create_call_metadata(self, channel_id, nonce, amount):
        mpe_address = self.get_mpe_address()
        signature = self._sign_message(mpe_address, channel_id, nonce, amount)
        return [("snet-payment-type",                 "escrow"),
                ("snet-payment-channel-id",            str(channel_id)),
                ("snet-payment-channel-nonce",         str(nonce)),
                ("snet-payment-channel-amount",        str(amount)),
                ("snet-payment-channel-signature-bin", bytes(signature)),
                ("snet-payment-mpe-address",           str(mpe_address))]

    def _deal_with_call_response(self, response):
        if (self.args.save_response):
            with open(self.args.save_response, "wb") as f:
                f.write(response.SerializeToString())
        elif (self.args.save_field):
            field = rgetattr(response, self.args.save_field[0])
            file_name = self.args.save_field[1]
            if (type(field) == bytes):
                with open(file_name, "wb") as f:
                    f.write(field)
            else:
                with open(file_name, "w") as f:
                    f.write(str(field))
        else:
            self._printout(response)

    def _get_endpoint_from_metadata_or_args(self, metadata):
        if (self.args.endpoint):
            return self.args.endpoint
        endpoints = metadata.get_all_endpoints_for_group(self.args.group_name)
        if (not endpoints):
            raise Exception(
                "Cannot find endpoint in metadata for the given payment group.")
        if (len(endpoints) > 1):
            self._printerr(
                "There are several endpoints for the given payment group. We will select %s" % endpoints[0])
        return endpoints[0]

    def call_server_lowlevel(self):


        self._init_or_update_registered_org_if_needed()
        self._init_or_update_registered_service_if_needed()

        params = self._get_call_params()
        service_metadata = self._get_service_metadata()
        endpoint = self._get_endpoint_from_metadata_or_args(service_metadata)
        grpc_channel = open_grpc_channel(endpoint)

        response = self._call_server_via_grpc_channel(
            grpc_channel, self.args.channel_id, self.args.nonce, self.args.amount_in_cogs, params, service_metadata)
        self._deal_with_call_response(response)

    # III. Stateless client related functions
    def _get_channel_state_from_server(self, grpc_channel, channel_id):

        # We should simply statically import everything, but it doesn't work because of the following issue in protobuf: https://github.com/protocolbuffers/protobuf/issues/1491
        #from snet_cli.resources.proto.state_service_pb2      import ChannelStateRequest            as request_class
        #from snet_cli.resources.proto.state_service_pb2_grpc import PaymentChannelStateServiceStub as stub_class
        proto_dir = RESOURCES_PATH.joinpath("proto")
        stub_class, request_class, _ = import_protobuf_from_dir(
            proto_dir, "GetChannelState")
        current_block = self.ident.w3.eth.blockNumber
        mpe_address = self.get_mpe_address()
        message = self.w3.soliditySha3(["string",             "address",    "uint256",   "uint256"],
                                       ["__get_channel_state", mpe_address, channel_id, current_block])
        signature = self.ident.sign_message_after_soliditySha3(message)

        request = request_class(channel_id=self.w3.toBytes(
            channel_id), signature=bytes(signature), current_block=current_block)

        stub = stub_class(grpc_channel)
        response = getattr(stub, "GetChannelState")(request)
        # convert bytes to int
        state = dict()
        state["current_nonce"] = int.from_bytes(
            response.current_nonce,         byteorder='big')
        state["current_signed_amount"] = int.from_bytes(
            response.current_signed_amount, byteorder='big')

        error_message = "Error in _get_channel_state_from_server. My own signature from the server is not valid."
        self._assert_validity_of_my_signature_or_zero_amount(bytes(
            response.current_signature),  channel_id, state["current_nonce"],     state["current_signed_amount"],  error_message)

        if (hasattr(response, "old_nonce_signed_amount")):
            state["old_nonce_signed_amount"] = int.from_bytes(
                response.old_nonce_signed_amount, byteorder='big')
            self._assert_validity_of_my_signature_or_zero_amount(bytes(
                response.old_nonce_signature), channel_id, state["current_nonce"] - 1, state["old_nonce_signed_amount"], error_message)

        return state

    def _calculate_unspent_amount(self, blockchain, server):
        if (server["current_nonce"] == blockchain["nonce"]):
            return blockchain["value"] - server["current_signed_amount"]
        if (server["current_nonce"] - 1 != blockchain["nonce"]):
            raise Exception("Server nonce is different from blockchain nonce to more then 1: server_nonce = %i blockchain_nonce = %i" % (
                server["current_nonce"], blockchain["nonce"]))

        if ("old_nonce_signed_amount" in server):
            return blockchain["value"] - server["old_nonce_signed_amount"] - server["current_signed_amount"]

        self._printerr(
            "Service is using old daemon which is not fully support stateless logic. Unspent amount might be overestimated")
        return blockchain["value"] - server["current_signed_amount"]

    def _get_channel_state_statelessly(self, grpc_channel, channel_id):
        """
        We get state of the channel (nonce, amount, unspent_amount)
        We do it by securely combine information from the server and blockchain
        https://github.com/singnet/wiki/blob/master/multiPartyEscrowContract/MultiPartyEscrow_stateless_client.md
        """
        server = self._get_channel_state_from_server(grpc_channel, channel_id)
        blockchain = self._get_channel_state_from_blockchain(channel_id)

        unspent_amount = self._calculate_unspent_amount(blockchain, server)

        return (server["current_nonce"], server["current_signed_amount"], unspent_amount)

    def print_channel_state_statelessly(self):
        grpc_channel = open_grpc_channel(self.args.endpoint)

        current_nonce, current_amount, unspent_amount = self._get_channel_state_statelessly(
            grpc_channel, self.args.channel_id)
        self._printout("current_nonce                  = %i" % current_nonce)
        self._printout("current_signed_amount_in_cogs  = %i" % current_amount)
        self._printout("current_unspent_amount_in_cogs = %s" %
                       str(unspent_amount))

    def _get_price_from_metadata(self, service_metadata, group_name):
        for group in service_metadata.m["groups"]:
            if group["group_name"] == group_name:
                pricings = group["pricing"]
                for pricing in pricings:
                    if (pricing["price_model"] == "fixed_price"):
                        return pricing["price_in_cogs"]
        raise Exception("We do not support price model: %s" %
                        (pricing["price_model"]))

    def call_server_statelessly_with_params(self, params, group_name):

        # if service is not initilized we will initialize it (unless we want skip registry check for update)
        if (not self.args.skip_update_check):
            self._init_or_update_registered_org_if_needed()
            self._init_or_update_registered_service_if_needed()

        org_metadata = self._read_metadata_for_org(self.args.org_id)
        service_metadata = self._get_service_metadata()
        endpoint = self._get_endpoint_from_metadata_or_args(service_metadata)
        grpc_channel = open_grpc_channel(endpoint)

        # if channel was not initilized we will try to initailize it (it will work only in simple case of signer == sender)
        channel = self._smart_get_initialized_channel_for_org(
            org_metadata, filter_by="signer")
        channel_id = channel["channelId"]
        price = self._get_price_from_metadata(service_metadata, group_name)
        server_state = self._get_channel_state_from_server(
            grpc_channel, channel_id)

        proceed = self.args.yes or input(
            "Price for this call will be %s AGI (use -y to remove this warning). Proceed? (y/n): " % (cogs2stragi(price))) == "y"
        if (not proceed):
            self._error("Cancelled")

        return self._call_server_via_grpc_channel(grpc_channel, channel_id, server_state["current_nonce"], server_state["current_signed_amount"] + price, params, service_metadata)

    def call_server_statelessly(self):
        group_name = self.args.group_name
        params = self._get_call_params()
        response = self.call_server_statelessly_with_params(params, group_name)
        self._deal_with_call_response(response)
