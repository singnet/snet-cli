""" Utils related to protobuf """
import sys
from pathlib import Path
import os


def import_protobuf_from_dir_for_given_service_name(proto_dir, service_name = None):
    """
    Dynamic import of grpc-protobuf from given directory (proto_dir)
    service_name should be provided only in the case of multiply grpc services
    Return stub_class, [response_classes], file_prefix

    ! We need response_classes only for json payload encoding !
    ! We need file_prefix to load all messages !
    """

    all_services = import_protobuf_from_dir_get_all(proto_dir)
    if (service_name is not None):
        if (service_name not in all_services):
            raise Exception("Error while loading protobuf. Cannot find service=%s"%service_name)
        return all_service[service_name]
    # service_name is None (was not specified)
    if (len(all_services) == 0):
        raise Exception("Error while loading protobuf. Cannot find any grpc services")
    if (len(all_services) > 1):
        raise Exception("Error while loading protobuf. Found serveral gprc services. Please specify service_name")
    return list(all_services.values())[0]


def import_protobuf_from_dir_get_all(proto_dir):
    """
    Helper function which dynamically import of grpc-protobuf from given directory (proto_dir)
    we return nested dictionary of all methods in all services
    return all_services[service_name] = (stub_class, methods_iodict, file_prefix)
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
                raise Exception("Error while loading protobuf. Found grpc service %s in multiply .proto files. We don't support packages yet!"%(service_name))
            all_services[service_name] = services[service_name]
    return all_services


def _import_protobuf_from_file_get_all(grpc_pyfile):
    """
    Helper function which dynamically import services from the given _pb2_grpc.py file
    we return nested dictionary of all services
    return all_services[service_name] = (stub_class, methods_iodict, file_prefix)
    """

    prefix = grpc_pyfile[:-12]
    pb2      = __import__("%s_pb2"%prefix)
    pb2_grpc = __import__("%s_pb2_grpc"%prefix)


    # we take all objects from pb2_grpc module which endswith "Stub", and we remove this postfix to get service_name
    all_service_names = [stub_name[:-4] for stub_name in dir(pb2_grpc) if stub_name.endswith("Stub")]

    rez = {}

    for service_name in all_service_names:
        stub_class         = getattr(pb2_grpc, "%sStub"%service_name)
        service_descriptor =  getattr(pb2, "DESCRIPTOR").services_by_name[service_name]
        methods_iodict     = { method.name: (method.input_type._concrete_class, method.output_type._concrete_class) for method in service_descriptor.methods }
        rez[service_name]  = (stub_class, methods_iodict, prefix)
    return rez
