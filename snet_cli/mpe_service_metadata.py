# functions for manipulate with server.json file
# metadata format:
#----------------------------------------------------
# version         - used to track format changes (current version is 1)
# model_ipfs_hash - IPFS HASH to the .tar archive of protobuf service specification
# mpe_address     - Address of MultiPartyEscrow contract. 
#                   Client should use it exclusively for cross-checking of mpe_address, 
#                        (because service can attack via mpe_address)
#                   Daemon can use it directly if authenticity of metadata is confirmed
# pricing {}      - Pricing model
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

class mpe_service_metadata:
    
    # init with modelIPFSHash
    def __init__(self):
        self.m = {"version"        : 1,
                  "model_ipfs_hash": "",
                  "mpe_address"    : "",
                  "pricing"        : {},
                  "groups"         : [],
                  "endpoints"      : []}
                  
    
    def set_model_ipfs_hash(self, model_ipfs_hash):
        self.m["model_ipfs_hash"] = model_ipfs_hash

    def set_mpe_address(self, mpe_address):
        self.m["mpe_address"] = mpe_address
        
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
                              "group_id"        : str(group_id_base64),
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
        # TODO: we probaly should check th  consistensy of loaded json here
        #       check that it contains required fields
        self.m = json.loads(j)
        
    def load(self, file_name):        
        with open(file_name) as f:
            self.set_from_json(json.load(f))
    
    def save(self, file_name):
        with open(file_name, 'w') as f:
            json.dump(self.get_json(), f)


def load_mpe_service_metadata(f):
    metadata = mpe_service_metadata()
    metadata.load(f)
    return metadata
