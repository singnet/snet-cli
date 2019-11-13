# run daemon
cd ../../snet_cli/test/functional_tests/simple_daemon
python test_simple_daemon.py &
DAEMON=$!
cd ..

snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529 --fixed-price 0.0001 --endpoints 127.0.0.1:50051
snet account deposit 12345 -y -q
snet organization create testo --org-id testo -y -q
snet service publish testo tests -y -q
snet service print-service-status testo tests

#/home/circleci/singnet/snet-cli/packages

cd ../../../sdk/test
snet sdk generate-client-library python testo tests
mv client_libraries/testo/tests/python/* .
