""" Utils related to protobuf """
import sys
from pathlib import Path
import os
from google.protobuf import json_format

from snet.snet_cli.utils import add_to_path


def import_all_grpc_methods_from_dir(proto_dir):
    """
    Dynamic import of grpc-protobuf from given directory (proto_dir)
    Neither service_name nor method_name need to be provided as each method will be imported using its fully qualified method name.
    Returns a map of method name => stub_class, request_class, response_class
    """
    proto_dir = Path(proto_dir)
    grpc_pyfiles = [str(os.path.basename(p)) for p in proto_dir.glob("*_pb2_grpc.py")]

    found_methods = dict()
    with add_to_path(str(proto_dir)): # <SERVICE>_pb2_grpc.py import <SERVICE>_pb2.py so we are forced to add proto_dir to path
        for grpc_pyfile in grpc_pyfiles:
            is_found, imported_methods = _import_protobuf_from_file(grpc_pyfile);
            if is_found:
                for fully_qualified_method_name, rez in imported_methods.items():
                    found_methods[fully_qualified_method_name] = rez

    return found_methods


def import_protobuf_from_dir(proto_dir, method_name, service_name = None):
    """
    Dynamic import of grpc-protobuf from given directory (proto_dir)
    service_name should be provided only in the case of conflicting method names (two methods with the same name in difference services).
    Return stub_class, request_class, response_class
    ! We need response_class only for json payload encoding !
    """
    proto_dir = Path(proto_dir)
    grpc_pyfiles = [str(os.path.basename(p)) for p in proto_dir.glob("*_pb2_grpc.py")]
    
    good_rez = []
    with add_to_path(str(proto_dir)): # <SERVICE>_pb2_grpc.py import <SERVICE>_pb2.py so we are forced to add proto_dir to path
        for grpc_pyfile in grpc_pyfiles:
            is_found, imported_methods = _import_protobuf_from_file(grpc_pyfile);
            if is_found: 
                for fully_qualified_method_name, rez in imported_methods.items():
                    try:
                        package, service, method = fully_qualified_method_name.split(".")
                    except:
                        service, method = fully_qualified_method_name.split(".")
                    if method == method_name and (service_name is None or service == service_name):
                        good_rez.append(rez)

    if (len(good_rez) == 0):
        raise Exception("Error while loading protobuf. Cannot find method=%s"%method_name)
    if (len(good_rez) > 1):
        if (service_name):
            raise Exception("Error while loading protobuf. Found method %s.%s in multiply .proto files. We don't support packages yet!"%(service_name, method_name))
        else:
            raise Exception("Error while loading protobuf. Found method %s in multiply .proto files. You could try to specify service_name."%method_name)
    return good_rez[0]


def _import_protobuf_from_file(grpc_pyfile):
    """
    helper function which imports all methods from the given _pb2_grpc.py file
    return (False, None)  in case of failure
    return (True, <dict of fully_qualified_method_name => (stub_class, request_class, response_class)> in case of success
    """
    
    prefix = grpc_pyfile[:-12]
    pb2      = __import__("%s_pb2"%prefix)
    pb2_grpc = __import__("%s_pb2_grpc"%prefix) 
    
    
    # we take all objects from pb2_grpc module which endswith "Stub", and we remove this postfix to get service_name
    all_service_names = [stub_name[:-4] for stub_name in dir(pb2_grpc) if stub_name.endswith("Stub")]
    
    found_services = dict()
    for service_name in all_service_names:
        service_descriptor =  getattr(pb2, "DESCRIPTOR").services_by_name[service_name]
        for method in service_descriptor.methods:
            request_class      = method.input_type._concrete_class
            response_class     = method.output_type._concrete_class
            stub_class         = getattr(pb2_grpc, "%sStub"%service_name)

            found_services[method.full_name] = (stub_class, request_class, response_class)
    if (len(found_services) == 0):
        return False, None
    return True, found_services


def switch_to_json_payload_encoding(call_fn, response_class):
    """ Switch payload encoding to JSON for GRPC call """
    def json_serializer(*args, **kwargs):
        return bytes(json_format.MessageToJson(args[0], True, preserving_proto_field_name=True), "utf-8")
    def json_deserializer(*args, **kwargs):
        resp = response_class()
        json_format.Parse(args[0], resp, True)
        return resp
    call_fn._request_serializer    = json_serializer
    call_fn._response_deserializer = json_deserializer
