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


class MPEClientCommand(BlockchainCommand):
    
    # I. Signature related functions
    def _sign_message(self):
        # here it is ok to accept address without checksum
        mpe_address = self._safe_to_checksum_address(self.args.mpe_address, error_message = "Wrong format of MultiPartyEscrow address")
        
        message = self.w3.soliditySha3(
        ["address",   "uint256",            "uint256",       "uint256"],
        [mpe_address, self.args.channel_id, self.args.nonce, self.args.amount])
        
        sign = self.ident.sign_message_after_soliditySha3(message)
        return sign    
    
    def print_sign_message(self):
        sign = self._sign_message()
        self._printout("signature hex: ")
        self._printout(sign.hex())
        self._printout("signature base64: ")
        self._printout(base64.b64encode(sign))

    def _verify_signature_base64(self):
        # here it is ok to accept address without checksum
        mpe_address = self._safe_to_checksum_address(self.args.mpe_address, error_message = "Wrong format of MultiPartyEscrow address")
        
        message = self.w3.soliditySha3(
        ["address",   "uint256",            "uint256",       "uint256"],
        [mpe_address, self.args.channel_id, self.args.nonce, self.args.amount])
        
        message_hash = defunct_hash_message(message)
        a = self.ident.w3.eth.account.recoverHash(message_hash, signature=base64.b64decode(self.args.signature_base64))
        return a == self.ident.address
    
    def print_verify_signature_base64(self):
        self._printout(self._verify_signature_base64())

    def _safe_to_checksum_address(self, a, error_message):
        try:
            return self.w3.toChecksumAddress(a)
        except ValueError:
            self._printerr(error_message)
            raise
        
    # II. Call related functions
    
    # complie protobuf for the given payment channel
    def compile_protobuf_from_file(self):
        codegen_dir = self.get_channel_dir()
        compile_proto(self.args.proto_dir, codegen_dir, proto_file=self.args.proto_file)
    
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
        
    def _import_protobuf_for_channel(self):
        channel_dir = self.get_channel_dir()
        pfiles = [str(os.path.basename(p)) for p in channel_dir.glob("*.py")]
        if (len(pfiles) != 2):
            self._error("We should have exactly two .py files in %s\n"%channel_dir +
                        "You should remove %s/.py and run _compile_from_file again"%channel_dir)

        # normally we should use importlib for import (see https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path)
        # but here we cannot do it because <SERVICE>_pb2_grpc.py import <SERVICE>_pb2.py ... 
        # so we were forced to play with sys.path
        sys.path.append(str(channel_dir))
        
        # make import 
        for p in pfiles:
            
            to_import = p.replace(".py","")
            # we check that we cannot be attacked via exec (check to_import)
            self._check_isidentifier(to_import)
            exec("import %s"%to_import, globals())
            
        service_name = pfiles[0].split("_")[0]   
        
        # we check that we cannot be attacked via eval (check service_name)
        self._check_isidentifier(service_name)
        stub_class = eval("%s_pb2_grpc.%sStub"%(service_name, service_name))
        
        service_descriptor = eval("%s_pb2.DESCRIPTOR.services_by_name['%s']"%(service_name, service_name))
        is_found = False
        for method in service_descriptor.methods:
            if(method.name == self.args.method):
                request_name  = method.input_type.name
                response_name = method.output_type.name
                is_found = True
                
        if (not is_found):
            self._error("Cannot find method %s in the protobuf"%(self.args.method))
        
        request_class = eval("%s_pb2.%s"%(service_name, request_name))

        return stub_class, request_class

    def _check_isidentifier(self, s):
        if (not s.isidentifier()):
            self._error('"%s" is not an identifier'%s)
        
    def call_server(self):
        params  = self._get_call_params()
        stub_class, request_class = self._import_protobuf_for_channel()
        request = request_class(**params)
        channel = grpc.insecure_channel(self.args.endpoint)
        
        stub    = stub_class(channel)
        call_fn = getattr(stub, self.args.method)
        
        signature = self._sign_message()
        metadata = [("snet-payment-type",                 "escrow"                    ),
                    ("snet-payment-channel-id",            str(self.args.channel_id)  ), 
                    ("snet-payment-channel-nonce",         str(self.args.nonce)       ), 
                    ("snet-payment-channel-amount",        str(self.args.amount)      ),
                    ("snet-payment-channel-signature-bin", base64.b64encode(signature))]
        
        response = call_fn(request, metadata=metadata)
        self._printout(response)
