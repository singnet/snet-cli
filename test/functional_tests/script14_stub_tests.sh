# script13

# run daemon
cd simple_daemon
python test_simple_daemon.py &
DAEMON=$!
cd ..


snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529 --fixed-price 0.0001 --endpoints 127.0.0.1:50051
snet account deposit 12345 -y -q
snet organization create testo --org-id testo -y -q
snet service publish testo tests -y -q
snet channel open-init testo tests 1 +10days -yq

python script14_stub_tests.py

kill $DAEMON
