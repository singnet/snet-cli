import enum
import importlib
from urllib.parse import urlparse

import grpc
import web3

from snet.sdk.root_certificate import root_certificate
from snet.snet_cli.utils.utils import RESOURCES_PATH, add_to_path


# for local debug
# from snet.snet_cli.resources.proto import training_pb2_grpc
# from snet.snet_cli.resources.proto import training_pb2


# from daemon code
class ModelMethodMessage(enum.Enum):
    CreateModel = "__CreateModel"
    GetModelStatus = "__GetModelStatus"
    UpdateModelAccess = "__UpdateModelAccess"
    GetAllModels = "__UpdateModelAccess"
    DeleteModel = "__GetModelStatus"


class TrainingModel:

    def __init__(self):
        with add_to_path(str(RESOURCES_PATH.joinpath("proto"))):
            self.training_pb2 = importlib.import_module("training_pb2")

        with add_to_path(str(RESOURCES_PATH.joinpath("proto"))):
            self.training_pb2_grpc = importlib.import_module("training_pb2_grpc")

    def _invoke_model(self, service_client, msg: ModelMethodMessage):
        org_id, service_id, group_id, daemon_endpoint = service_client.get_service_details()

        endpoint_object = urlparse(daemon_endpoint)
        if endpoint_object.port is not None:
            channel_endpoint = endpoint_object.hostname + ":" + str(endpoint_object.port)
        else:
            channel_endpoint = endpoint_object.hostname

        if endpoint_object.scheme == "http":
            print("creating http channel: ", channel_endpoint)
            channel = grpc.insecure_channel(channel_endpoint)
        elif endpoint_object.scheme == "https":
            channel = grpc.secure_channel(channel_endpoint,
                                          grpc.ssl_channel_credentials(root_certificates=root_certificate))
        else:
            raise ValueError('Unsupported scheme in service metadata ("{}")'.format(endpoint_object.scheme))

        current_block_number = service_client.get_current_block_number()
        signature = service_client.generate_training_signature(msg.value, web3.Web3.to_checksum_address(
            service_client.account.address), current_block_number)
        auth_req = self.training_pb2.AuthorizationDetails(signature=bytes(signature),
                                                          current_block=current_block_number,
                                                          signer_address=service_client.account.address,
                                                          message=msg.value)
        return auth_req, channel

    # params from AI-service: status, model_id
    # params pass to daemon: grpc_service_name, grpc_method_name, address_list,
    # description, model_name, training_data_link, is_public_accessible
    def create_model(self, service_client, grpc_method_name: str, model_name: str,
                     description: str = '',
                     training_data_link: str = '', grpc_service_name='service',
                     is_publicly_accessible=False, address_list: list[str] = None):
        if address_list is None:
            address_list = []
        try:
            auth_req, channel = self._invoke_model(service_client, ModelMethodMessage.CreateModel)
            model_details = self.training_pb2.ModelDetails(grpc_method_name=grpc_method_name, description=description,
                                                           training_data_link=training_data_link,
                                                           grpc_service_name=grpc_service_name,
                                                           model_name=model_name, address_list=address_list,
                                                           is_publicly_accessible=is_publicly_accessible)
            stub = self.training_pb2_grpc.ModelStub(channel)
            response = stub.create_model(
                self.training_pb2.CreateModelRequest(authorization=auth_req, model_details=model_details))
            return response
        except Exception as e:
            print("Exception: ", e)
            return e

    # params from AI-service: status
    # params to daemon: grpc_service_name, grpc_method_name, model_id
    def get_model_status(self, service_client, model_id: str, grpc_method_name: str, grpc_service_name='service'):
        try:
            auth_req, channel = self._invoke_model(service_client, ModelMethodMessage.GetModelStatus)
            model_details = self.training_pb2.ModelDetails(grpc_method_name=grpc_method_name,
                                                           grpc_service_name=grpc_service_name, model_id=str(model_id))
            stub = self.training_pb2_grpc.ModelStub(channel)
            response = stub.get_model_status(
                self.training_pb2.ModelDetailsRequest(authorization=auth_req, model_details=model_details))
            return response
        except Exception as e:
            print("Exception: ", e)
            return e

    # params from AI-service: status
    # params to daemon: grpc_service_name, grpc_method_name, model_id
    def delete_model(self, service_client, model_id: str, grpc_method_name: str,
                     grpc_service_name='service'):
        try:
            auth_req, channel = self._invoke_model(service_client, ModelMethodMessage.DeleteModel)
            model_details = self.training_pb2.ModelDetails(grpc_method_name=grpc_method_name,
                                                           grpc_service_name=grpc_service_name, model_id=str(model_id))
            stub = self.training_pb2_grpc.ModelStub(channel)
            response = stub.delete_model(
                self.training_pb2.UpdateModelRequest(authorization=auth_req, update_model_details=model_details))
            return response
        except Exception as e:
            print("Exception: ", e)
            return e

    # params from AI-service: None
    # params to daemon: grpc_service_name, grpc_method_name, model_id, address_list, is_public, model_name, desc
    # all params required
    def update_model_access(self, service_client, model_id: str, grpc_method_name: str,
                            model_name: str, is_public: bool,
                            description: str, grpc_service_name: str = 'service', address_list: list[str] = None):
        try:
            auth_req, channel = self._invoke_model(service_client, ModelMethodMessage.UpdateModelAccess)
            model_details = self.training_pb2.ModelDetails(grpc_method_name=grpc_method_name, description=description,
                                                           grpc_service_name=grpc_service_name,
                                                           address_list=address_list,
                                                           is_publicly_accessible=is_public, model_name=model_name,
                                                           model_id=str(model_id))
            stub = self.training_pb2_grpc.ModelStub(channel)
            response = stub.update_model_access(
                self.training_pb2.UpdateModelRequest(authorization=auth_req, update_model_details=model_details))
            return response
        except Exception as e:
            print("Exception: ", e)
            return e

    # params from AI-service: None
    # params to daemon: grpc_service_name, grpc_method_name
    def get_all_models(self, service_client, grpc_method_name: str, grpc_service_name='service'):
        try:
            auth_req, channel = self._invoke_model(service_client, ModelMethodMessage.GetAllModels)
            stub = self.training_pb2_grpc.ModelStub(channel)
            response = stub.get_all_models(
                self.training_pb2.AccessibleModelsRequest(authorization=auth_req, grpc_service_name=grpc_service_name,
                                                          grpc_method_name=grpc_method_name))
            return response
        except Exception as e:
            print("Exception: ", e)
            return e