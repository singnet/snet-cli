# simple case of one group
snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529 --fixed-price 0.0001 --endpoints 8.8.8.8:2020
snet organization create testo --org-id testo -y -q
snet service publish testo tests -y -q

snet sdk generate-client-library python testo tests
test -f client_libraries/testo/tests/python/ExampleService_pb2_grpc.py

snet sdk generate-client-library nodejs testo tests
test -f client_libraries/testo/tests/nodejs/ExampleService_grpc_pb.js

# test relative path (and using already installed compiler)
snet sdk generate-client-library nodejs testo tests snet_output
test -f snet_output/testo/tests/nodejs/ExampleService_grpc_pb.js

# test absolute path
snet sdk generate-client-library nodejs testo tests /tmp/snet_output
test -f /tmp/snet_output/testo/tests/nodejs/ExampleService_grpc_pb.js
