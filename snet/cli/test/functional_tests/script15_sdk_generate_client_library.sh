# simple case of one group
snet service metadata-init ./service_spec1/ ExampleService --group-name group1 --fixed-price 0.0001 --endpoints 8.8.8.8:2020
snet organization metadata-init org1 testo individual
snet organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 127.0.0.1:50051
snet organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 127.0.0.1:50051
snet organization create testo -y -q
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
