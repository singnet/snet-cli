import base64
from json import JSONEncoder

import json


class DefaultEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


class PaymentStorageClient(object):

    def __init__(self, connection_timeout=None, request_timeout="", endpoints=[]):
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        self.endpoints = endpoints

    def add_payment_storage_client_details(self, connection_time_out, request_timeout, endpoints):
        self.connection_timeout = connection_time_out
        self.request_timeout = request_timeout
        self.endpoints = endpoints

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)

    def validate(self):
        if len(self.endpoints) < 1:
            raise Exception(
                "At least on ednpoint is required for payment channel ")


class Payment(object):

    def __init__(self, payment_address="", payment_expiration_threshold="", payment_channel_storage_type="",
                 payment_channel_storage_client=PaymentStorageClient()):
        self.payment_address = payment_address
        self.payment_expiration_threshold = payment_expiration_threshold
        self.payment_channel_storage_type = payment_channel_storage_type
        self.payment_channel_storage_client = payment_channel_storage_client

    @classmethod
    def from_json(cls, json_data: dict):
        payment_channel_storage_client = PaymentStorageClient.from_json(
            json_data['payment_channel_storage_client'])
        return cls(json_data['payment_address'], json_data['payment_expiration_threshold'],
                   json_data['payment_channel_storage_type'], payment_channel_storage_client)

    def validate(self):
        if self.payment_address is None:
            raise Exception("Payment address cannot be null")
        if self.payment_channel_storage_type is None:
            raise Exception("Payment channel storage type cannot be null")
        if self.payment_expiration_threshold is None:
            raise Exception("Payment expiration threshold cannot be null")

        if self.payment_channel_storage_client is None:
            raise Exception("Payment channel storage client cannot be null")
        else:
            self.payment_channel_storage_client.validate()

    def update_connection_timeout(self, connection_timeout):
        self.payment_channel_storage_client.connection_timeout = connection_timeout

    def update_request_timeout(self, request_timeout):
        self.payment_channel_storage_client.request_timeout = request_timeout

    def update_endpoints(self, endpoints):
        self.payment_channel_storage_client.endpoints = endpoints


class Group(object):

    def __init__(self, group_name="", group_id="", payment=Payment()):
        self.group_name = group_name
        self.group_id = group_id
        self.payment = payment

    @classmethod
    def from_json(cls, json_data: dict):
        payment = Payment()
        if 'payment' in json_data:
            payment = Payment.from_json(json_data['payment'])
        return cls(json_data['group_name'], json_data['group_id'], payment)

    def add_group_details(self, group_name, group_id, payment):
        self.group_name = group_name
        self.group_id = group_id
        self.payment = payment

    def validate(self):
        if self.group_name is None:
            raise Exception("group name cannot be null")
        if self.group_id is None:
            raise Exception("group_id is cannot be null")

        if self.payment is None:
            raise Exception(
                "payment details cannot be null for group_name %s", self.group_name)
        else:
            self.payment.validate()

    def update_payment_expiration_threshold(self, payment_expiration_threshold):
        self.payment.payment_expiration_threshold = payment_expiration_threshold

    def update_payment_channel_storage_type(self, payment_channel_storage_type):
        self.update_payment_channel_storage_type = payment_channel_storage_type

    def update_payment_address(self, payment_address):
        self.payment.payment_address = payment_address

    def update_connection_timeout(self, connection_timeout):
        self.payment.update_connection_timeout(connection_timeout)

    def update_request_timeout(self, request_timeout):
        self.payment.update_request_timeout(request_timeout)

    def update_endpoints(self, endpoints):
        self.payment.update_endpoints(endpoints)

    def get_group_id(self, group_name=None):
        return base64.b64decode(self.get_group_id_base64(group_name))

    def get_payment_address(self):
        return self.payment.payment_address


class OrganizationMetadata(object):
    """
        Sample OrganizationMetadata
            {
               "org_name":"organization_name",
               "org_id":"org_id1",
               "groups":[
                  {
                     "group_name":"default_group2",
                     "group_id":"99ybRIg2wAx55mqVsA6sB4S7WxPQHNKqa4BPu/bhj+U=",
                     "payment":{
                        "payment_address":"0x671276c61943A35D5F230d076bDFd91B0c47bF09",
                        "payment_expiration_threshold":40320,
                        "payment_channel_storage_type":"etcd",
                        "payment_channel_storage_client":{
                           "connection_timeout":"5s",
                           "request_timeout":"3s",
                           "endpoints":[
                              "http://127.0.0.1:2379"
                           ]
                        }
                     }
                  },
                  {
                     "group_name":"default_group2",
                     "group_id":"99ybRIg2wAx55mqVsA6sB4S7WxPQHNKqa4BPu/bhj+U=",
                     "payment":{
                        "payment_address":"0x671276c61943A35D5F230d076bDFd91B0c47bF09",
                        "payment_expiration_threshold":40320,
                        "payment_channel_storage_type":"etcd",
                        "payment_channel_storage_client":{
                           "connection_timeout":"5s",
                           "request_timeout":"3s",
                           "endpoints":[
                              "http://127.0.0.1:2379"
                           ]
                        }
                     }
                  }
               ]
            }


    """

    def __init__(self, org_name="", org_id="", groups=[]):
        self.org_name = org_name
        self.org_id = org_id
        self.groups = groups

    def add_group(self, group):
        self.groups.append(group)

    def get_json_pretty(self):
        return json.dumps(self, indent=4, cls=DefaultEncoder)

    def save_pretty(self, file_name):
        with open(file_name, 'w') as f:
            f.write(self.get_json_pretty())

    @classmethod
    def from_json(cls, json_data: dict):
        groups = []
        if 'groups' in json_data:
            groups = list(map(Group.from_json, json_data["groups"]))
        return cls(json_data['org_name'], json_data['org_id'], groups)

    @classmethod
    def from_file(cls, filepath):
        with open(filepath) as f:
            return OrganizationMetadata.from_json(json.load(f))

    def validate(self):
        if self.org_id is None:
            raise Exception("Org_id cannot be null")
        if self.org_name is None:
            raise Exception("Org_name cannot be null")

        if len(self.groups) < 1:
            raise Exception(
                "At least One group is required to create an organization")
        else:
            for group in self.groups:
                group.validate()

    def get_payment_address_for_group(self, group_name):
        for group in self.groups:
            if group.group_name == group_name:
                return group.get_payment_address()

    def get_group_id_by_group_name(self, group_name):
        for group in self.groups:
            if group.group_name == group_name:
                return group.group_id

    def get_group_by_group_id(self, group_id):
        for group in self.groups:
            if group.group_id == group_id:
                return group

    # def get_group_by_group_name(self,group_name):
    #      return base64.b64decode(group_name)
