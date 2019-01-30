""" Utils related to protobuf """
import sys
from pathlib import Path
import os
from google.protobuf import json_format


def import_protobuf_from_dir(proto_dir, method_name, service_name = None):
    """
    Dynamic import of grpc-protobuf from given directory (proto_dir)
    service_name should be provided only in the case of conflicting method names (two methods with the same name in different services).
    Return stub_class, request_class, response_class
    ! We need response_class only for json payload encoding !
    """
    all_services =  import_protobuf_from_dir_get_all(proto_dir)

    if (service_name):
        if (service_name not in all_services):
            raise Exception("Error while loading protobuf. Cannot find service=%s"%service_name)
        if (method_name not in all_services[service_name]):
            raise Exception("Error while loading protobuf. Cannot find method=%s in service=%s"%(method_name,service_name))
        return all_services[service_name][method_name]
    found_services = [n for n in all_services if method_name in all_services[n]]
    if (len(found_services) == 0):
        raise Exception("Error while loading protobuf. Cannot find method=%s"%method_name)
    if (len(found_services) > 1):
        raise Exception("Error while loading protobuf. We found methods %s in multiply services [%s]."
                        " You should specify service_name."%(method_name, ", ".join(found_services)))

    return all_services[found_services[0][method_name]]


def import_protobuf_from_dir_get_all(proto_dir):
    """
    Helper function which dynamically import of grpc-protobuf from given directory (proto_dir)
    we return nested dictionary of all methods in all services
    return all_services[service_name][method_name] = (stub_class, request_class, response_class)
    """

    proto_dir = Path(proto_dir)
    # <SERVICE>_pb2_grpc.py import <SERVICE>_pb2.py so we are forced to add proto_dir to path
    sys.path.append(str(proto_dir))
    grpc_pyfiles = [str(os.path.basename(p)) for p in proto_dir.glob("*_pb2_grpc.py")]

    all_services = {}
    for grpc_pyfile in grpc_pyfiles:
        services = _import_protobuf_from_file_get_all(grpc_pyfile)

        for service_name in services:
            if (service_name in all_services):

                # check for possible conflict
                for method_name in services[service_name]:
                    if (method_name in all_services[service_name]):
                        raise Exception("Error while loading protobuf. Found method %s.%s in multiply .proto files. We don't support packages yet!"%(service_name, method_name))
                    all_services[service_name][method_name] = services[service_name][method_name]
            else:
                all_services[service_name] = services[service_name]
    return all_services


def _import_protobuf_from_file_get_all(grpc_pyfile):
    """
    Helper function which dynamically import services from the given _pb2_grpc.py file
    we return nested dictionary of all methods in all services
    return all_services[service_name][method_name] = (stub_class, request_class, response_class)
    """

    prefix = grpc_pyfile[:-12]
    pb2      = __import__("%s_pb2"%prefix)
    pb2_grpc = __import__("%s_pb2_grpc"%prefix)


    # we take all objects from pb2_grpc module which endswith "Stub", and we remove this postfix to get service_name
    all_service_names = [stub_name[:-4] for stub_name in dir(pb2_grpc) if stub_name.endswith("Stub")]

    rez = { s:{} for s in all_service_names}

    for service_name in all_service_names:
        service_descriptor =  getattr(pb2, "DESCRIPTOR").services_by_name[service_name]
        for method in service_descriptor.methods:
            request_class      = getattr(pb2, method.input_type.name)
            response_class     = getattr(pb2, method.output_type.name)
            stub_class         = getattr(pb2_grpc, "%sStub"%service_name)
            rez[service_name][method.name] = (stub_class, request_class, response_class)
    return rez


def switch_to_json_payload_econding(call_fn, response_class):
    """ Switch payload encoding to JSON for GRPC call """
    def json_serializer(*args, **kwargs):
        return bytes(json_format.MessageToJson(args[0], True, preserving_proto_field_name=True), "utf-8")
    def json_deserializer(*args, **kwargs):
        resp = response_class()
        json_format.Parse(args[0], resp, True)
        return resp
    call_fn._request_serializer    = json_serializer
    call_fn._response_deserializer = json_deserializer
