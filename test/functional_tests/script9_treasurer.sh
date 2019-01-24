# Test 'snet treasurer'

# run daemon
cd simple_daemon
python test_simple_daemon.py &
DAEMON=$!
cd ..


snet account deposit 12345 -y -q

# service provider has --wallet-index==9 (0x52653A9091b5d5021bed06c5118D24b23620c529)
snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529 --fixed-price 0.0001 --endpoints 127.0.0.1:50051


assert_balance () {
MPE_BALANCE=$(snet account balance --account 0x52653A9091b5d5021bed06c5118D24b23620c529 |grep MPE)
test ${MPE_BALANCE##*:} = $1
}

EXPIRATION0=$((`snet channel block-number` + 100))
EXPIRATION1=$((`snet channel block-number` + 100000))
EXPIRATION2=$((`snet channel block-number` + 100000))
snet channel open-init-metadata 1 $EXPIRATION0 -yq
snet channel open-init-metadata 1 $EXPIRATION1 -yq
snet channel open-init-metadata 1 $EXPIRATION2 -yq

snet client call 0 0.0001 127.0.0.1:50051 classify {}
snet client call 0 0.0001 127.0.0.1:50051 classify {} --save-response response.pb
snet client call 1 0.0001 127.0.0.1:50051 classify {} --save-field binary_field out.bin
snet client call 2 0.0001 127.0.0.1:50051 classify {} --save-field predictions out.txt
rm -f response.pb out.bin out.txt
snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
assert_balance 0.0004
snet client call 0 0.0001 127.0.0.1:50051 classify {}
snet client call 0 0.0001 127.0.0.1:50051 classify {}
snet client call 1 0.0001 127.0.0.1:50051 classify {}
snet client call 2 0.0001 127.0.0.1:50051 classify {}

#only channel 0 should be claimed
snet treasurer claim-expired --expiration-threshold 1000 --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
assert_balance 0.0006
snet treasurer claim 1 2 --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
assert_balance 0.0008

snet client call 0 0.0001 127.0.0.1:50051 classify {}
snet client call 0 0.0001 127.0.0.1:50051 classify {}
snet client call 1 0.0001 127.0.0.1:50051 classify {}
snet client call 2 0.0001 127.0.0.1:50051 classify {}

# we will start claim of all channels but will not write then to blockchain
echo n | snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 && exit 1 || echo "fail as expected"
assert_balance 0.0008

snet client call 1 0.0001 127.0.0.1:50051 classify {}
snet client call 2 0.0001 127.0.0.1:50051 classify {}

# and now we should claim everything (including pending payments)
snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 -yq 
assert_balance 0.0014

kill $DAEMON
