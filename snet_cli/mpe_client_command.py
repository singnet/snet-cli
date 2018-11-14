from snet_cli.commands import BlockchainCommand
from snet_cli.utils import compile_proto
import base64
from pathlib import Path
import json
import sys
import os 
import importlib
import grpc
from eth_account.messages import defunct_hash_message
from web3.utils.encoding import pad_hex
from web3.utils.events import get_event_data
from snet_cli.utils import get_contract_def, abi_get_element_by_name, abi_decode_struct_to_dict
from snet_cli.utils_proto import import_protobuf_from_dir, switch_to_json_payload_econding


class MPEClientCommand(BlockchainCommand):
    
    # I. Signature related functions
    
    def _compose_message_to_sign(self, mpe_address, channel_id, nonce, amount):
        # here it is ok to accept address without checksum
        mpe_address = self._safe_to_checksum_address(mpe_address, error_message = "Wrong format of MultiPartyEscrow address")

        return self.w3.soliditySha3(
               ["address",   "uint256", "uint256", "uint256"],
               [mpe_address, channel_id, nonce,     amount])
    
    def _sign_message(self, mpe_address, channel_id, nonce, amount):
        message = self._compose_message_to_sign(mpe_address, channel_id, nonce, amount)
        sign    = self.ident.sign_message_after_soliditySha3(message)
        return sign    
    
    def print_sign_message(self):
        sign = self._sign_message(self.args.mpe_address, self.args.channel_id, self.args.nonce, self.args.amount)
        self._printout("signature hex: ")
        self._printout(sign.hex())
        self._printout("signature base64: ")
        self._printout(base64.b64encode(sign))

    def _verify_my_signature(self, signature, mpe_address, channel_id, nonce, amount):
        message      = self._compose_message_to_sign(mpe_address, channel_id, nonce, amount)
        message_hash = defunct_hash_message(message)
        sign_address = self.ident.w3.eth.account.recoverHash(message_hash, signature=signature)
        return sign_address == self.ident.address
    
    def print_verify_my_signature_base64(self):
        signature = base64.b64decode(self.args.signature_base64)
        rez       = self._verify_my_signature(signature, self.args.mpe_address, self.args.channel_id, self.args.nonce, self.args.amount)
        self._printout(rez)

    def _safe_to_checksum_address(self, a, error_message):
        try:
            return self.w3.toChecksumAddress(a)
        except ValueError:
            self._printerr(error_message)
            raise
        
    # II. Call related functions
    
    # complie protobuf for the given payment channel
    def compile_protobuf_from_dir(self):
        codegen_dir = self.get_channel_dir()
        if (not compile_proto(Path(self.args.proto_dir), codegen_dir)):
            self._error("Fail to compile %s/*.proto"%self.args.proto_dir)
    
    # get persistent storage for the given channel (~/.snet/mpe_client/<channel-id>/)
    def get_channel_dir(self):
        return Path.home().joinpath(".snet", "mpe_client", str(self.args.channel_id))
   
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

    # possible modifiers: file, b64encode, b64decode
    # format:             modifier1@modifier2@...modifierN@k_final
    def _transform_call_params(self, params):
        rez = {}
        for k, v in params.items(): 
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
                    raise Exception("Unknow modifier ('%s') in call parameters. Possible modifiers: file, b64encode, b64decode"%m)
            rez[k_final] = v
        return rez
            
    def _import_protobuf_for_channel(self, service_name, method_name):
        channel_dir = self.get_channel_dir()
        return import_protobuf_from_dir(channel_dir, method_name, service_name)

    def _call_server_withchannel(self, grpc_channel, service, method, mpe_address, channel_id, nonce, amount, params, is_json_encoding):
        stub_class, request_class, response_class = self._import_protobuf_for_channel(service, method)
        
        request  = request_class(**params)
        stub     = stub_class(grpc_channel)
        call_fn  = getattr(stub, self.args.method)
        
        if is_json_encoding:
            switch_to_json_payload_econding(call_fn, response_class)
        
        signature = self._sign_message(mpe_address, channel_id, nonce, amount)
        metadata = [("snet-payment-type",                 "escrow"                    ),
                    ("snet-payment-channel-id",            str(channel_id)  ), 
                    ("snet-payment-channel-nonce",         str(nonce)       ), 
                    ("snet-payment-channel-amount",        str(amount)      ),
                    ("snet-payment-channel-signature-bin", bytes(signature))]
        
        response = call_fn(request, metadata=metadata)
        return response
        
    def call_server_lowlevel(self):
        params                    = self._get_call_params()
        grpc_channel              = grpc.insecure_channel(self.args.endpoint)
        
        response = self._call_server_withchannel(grpc_channel, self.args.service, self.args.method, 
                                                 self.args.mpe_address, self.args.channel_id, self.args.nonce, self.args.amount, 
                                                 params, self.args.json)
        self._printout(response)
        
    # III. Stateless client related functions 
    
    def print_my_channels(self):
        # TODO: check that it is faster to use events to get all channels with the given sender (instead of using channels directly)
        event_signature   = self.ident.w3.sha3(text="EventChannelOpen(uint256,address,address,uint256)").hex()
        my_address_padded = pad_hex(self.ident.address.lower(), 256)
        logs = self.ident.w3.eth.getLogs({"fromBlock" : self.args.from_block,
                                          "address"   : self.args.mpe_address.lower(),
                                          "topics"    : [event_signature,  my_address_padded]})
        
        # If we are sure that ABI will be fixed forever we can do like this:
        # channels_ids = [int(l['data'],16) for l in logs]
        abi           = get_contract_def("MultiPartyEscrow")
        event_abi     = abi_get_element_by_name(abi, "EventChannelOpen")
        channels_ids  = [get_event_data(event_abi, l)["args"]["channelId"] for l in logs]
        
        channel_abi = abi_get_element_by_name(abi, "channels")
        
        self._printout("#id nonce recipient  groupId  value   expiration(blocks)")
        for i in channels_ids:
            channel = self.call_contract_command("MultiPartyEscrow", self.args.mpe_address, "channels", [i])
            channel = abi_decode_struct_to_dict(channel_abi, channel)
            self._printout("%i %i %s %i %i %i"%(i, channel["nonce"], channel["recipient"], channel["groupId"],
                                                channel["value"], channel["expiration"]))
    
    def _get_channel_state_from_server(self, grpc_channel, mpe_address, channel_id):
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
         good = self._verify_my_signature(bytes(response.current_signature), mpe_address, channel_id, state["current_nonce"], state["current_signed_amount"])
         if (not good):
             raise Exception("Error in _get_channel_state_from_server. My own signature from the server is not valid.")
             
        return state

    def print_channel_state_from_server(self):
        grpc_channel = grpc.insecure_channel(self.args.endpoint)         
        state     = self._get_channel_state_from_server(grpc_channel, self.args.mpe_address, self.args.channel_id)
        self._printout(state)
        
    def _get_channel_state_from_blockchain(self, mpe_address, channel_id):
        abi         = get_contract_def("MultiPartyEscrow")
        channel_abi = abi_get_element_by_name(abi, "channels")
        channel     = self.call_contract_command("MultiPartyEscrow", self.args.mpe_address, "channels", [channel_id])
        channel     = abi_decode_struct_to_dict(channel_abi, channel)
        return channel
    
    # we get state of the channel (nonce, amount, unspent_amount)
    # We do it by securely combine information from the server and blockchain
    # https://github.com/singnet/wiki/blob/master/multiPartyEscrowContract/MultiPartyEscrow_stateless_client.md
    def _get_channel_state_statelessly(self, grpc_channel, mpe_address, channel_id):
        server     = self._get_channel_state_from_server    (grpc_channel, mpe_address, channel_id)
        blockchain = self._get_channel_state_from_blockchain(              mpe_address, channel_id)
        
        if (server["current_nonce"] == blockchain["nonce"]):
            unspent_amount = blockchain["value"] - server["current_signed_amount"]
        else:
            unspent_amount = None # in this case we cannot securely define unspent_amount yet
        
        return (server["current_nonce"], server["current_signed_amount"], unspent_amount)
        
    
    def call_server_statelessly(self):
        params                    = self._get_call_params()
        grpc_channel              = grpc.insecure_channel(self.args.endpoint)
                
        current_nonce, current_amount, unspent_amount = self._get_channel_state_statelessly(grpc_channel, self.args.mpe_address, self.args.channel_id)
        self._printout("unspent_amount before call (None means that we cannot get it now):%s"%str(unspent_amount))
        response = self._call_server_withchannel(grpc_channel, self.args.service, self.args.method,
                                                 self.args.mpe_address, self.args.channel_id, current_nonce, current_amount + self.args.price, 
                                                 params, self.args.json)
        self._printout(response)
        
        
    #IV. Auxilary functions
    
    # get the most recent block number
    def print_block_number(self):
         self._printout(self.ident.w3.eth.blockNumber)
