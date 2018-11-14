# functions for manipulate service metadata
# metadata format:
#----------------------------------------------------
# version          - used to track format changes (current version is 1)
# display_name     - Display name of the service
# encoding         - Service encoding (json or grpc)
# service_type     - Service type (grpc, jsonrpc or process)  
# payment_expiration_threshold - Service will reject payments with expiration less
#                                than current_block + payment_expiration_threshold.
#                                This field should be used by the client with caution.
#                                Client should not accept arbitrary payment_expiration_threshold
# model_ipfs_hash  - IPFS HASH to the .tar archive of protobuf service specification
# mpe_address      - Address of MultiPartyEscrow contract. 
#                    Client should use it exclusively for cross-checking of mpe_address, 
#                         (because service can attack via mpe_address)
#                    Daemon can use it directly if authenticity of metadata is confirmed
# pricing {}      -  Pricing model
#          Possible pricing models:
#          1. Fixed price
#              price_model  - "fixed_price"
#              price        -  unique fixed price for all method
#              (other pricing models can be easily supported)
# groups[]       - group is the number of endpoints which shares same payment channel; 
#                   grouping strategy is defined by service provider; 
#                   for example service provider can use region name as group name
#      group_name - unique name of the group (human readable)
#      group_id   - unique id of the group (random 32 byte string in base64 encoding)
#      payment_address - Ethereum address to recieve payments
#
#endpoints[] - address in the off-chain network to provide a service
#      group_name 
#      endpoint - 127.0.0.1:1234 (or http://127.0.0.1:1234) - unique endpoint identifier
#-------------------------------------------------------

import json
import base64
import secrets

# TODO: we should use some standart solution here
class mpe_service_metadata:
    
    # init with modelIPFSHash
    def __init__(self):
        self.m = {"version"        : 1,
                  "display_name"   : "",
                  "encoding"       : "grpc", # grpc by default
                  "service_type"   : "grpc", # grpc by default
                  "payment_expiration_threshold" : 40320, # one week by default (15 sec block,  24*60*60*7/15) 
                  "model_ipfs_hash": "",
                  "mpe_address"    : "",
                  "pricing"        : {},
                  "groups"         : [],
                  "endpoints"      : []}
                  
    
    def set_simple_field(self, f, v):
        if (f != "display_name" and f != "encoding" and f != "model_ipfs_hash" and f != "mpe_address" and
            f != "service_type" and f != "payment_expiration_threshold"):
                raise Exception("unknow field in mpe_service_metadata")
        self.m[f] = v        
        
    def set_fixed_price(self, price):
        if (type(price) != int): 
            raise Exception("Price should have int type")
        self.m["pricing"] = {"price_model" : "fixed_price",
                             "price"       : price}
                 
    # return new group_id in base64
    def add_group(self, group_name, payment_address):
        if (self._is_group_present(group_name)):
            raise Exception("the group \"%s\" is already present"%str(group_name))
        group_id_base64 = base64.b64encode(secrets.token_bytes(32))
        self.m["groups"] += [{"group_name"      : group_name , 
                              "group_id"        : group_id_base64.decode("ascii"),
                              "payment_address" : payment_address}]
        return group_id_base64
    
    def add_endpoint(self, group_name, endpoint):
        if (not self._is_group_present(group_name)):
            raise Exception("the group %s is not present"%str(group_name))
        e = {"group_name" : group_name, "endpoint"   : endpoint}
        if (e in self.m["endpoints"]):
            raise Exception("We already have endpoint %s in group %s"%(endpoint, group_name))
        self.m["endpoints"] += [e]
    
    # check if group is already present
    def _is_group_present(self, group_name):
        groups = self.m["groups"]
        for g in groups:
            if (g["group_name"] == group_name):
                return True
        return False

    def get_json(self):
        return json.dumps(self.m)
    
    def set_from_json(self, j):
        # TODO: we probaly should check the  consistensy of loaded json here
        #       check that it contains required fields
        self.m = json.loads(j)
        
    def load(self, file_name):        
        with open(file_name) as f:
            self.set_from_json(f.read())
    
    def save(self, file_name):
        with open(file_name, 'w') as f:
            json.dump(self.m, f)

    def __getitem__(self, key):
        return self.m[key]
    
    # In all getter function group_name == None works only in case of single payment group
    
    def get_group(self, group_name = None):
        groups = self.m["groups"]
        if (len(groups) == 0):
            raise Exception("Cannot find any groups in metadata")
        if (not group_name):
            if (len(groups) > 1):
                raise Exception("We have more than one payment group in metadata, so group_name should be specified")
            return groups[0]
        for g in groups:
            if (g["group_name"] == group_name):
                return g
        raise Exception('Cannot find group "%s" in metadata'%group_name)

    def get_group_id_base64(self, group_name = None):
        return self.get_group(group_name)["group_id"]

    def get_group_id(self, group_name = None):
        return base64.b64decode(self.get_group_id_base64(group_name))

    def get_payment_address(self, group_name = None):
        return self.get_group(group_name)["payment_address"]

    
def load_mpe_service_metadata(f):
    metadata = mpe_service_metadata()
    metadata.load(f)
    return metadata

def mpe_service_metadata_from_json(j):
    metadata      = mpe_service_metadata()
    metadata.set_from_json(j)
    return metadata
                    
