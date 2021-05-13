# Test 'snet treasurer'

# run daemon
cd simple_daemon
python test_simple_daemon.py &
DAEMON=$!
cd ..


snet account deposit 12345 -y -q

# service provider has --wallet-index==9 (0x52653A9091b5d5021bed06c5118D24b23620c529)
# make two endpoints (both are actually valid)

snet organization metadata-init org1 testo individual
snet organization add-group group0 0x52653A9091b5d5021bed06c5118D24b23620c529 5.5.6.7:8089
snet organization create testo -y -q




snet service metadata-init ./service_spec1/ ExampleService --group-name group0 --fixed-price 0.0001 --endpoints 127.0.0.1:50051
snet service publish testo tests -y -q



assert_balance () {
MPE_BALANCE=$(snet account balance --account 0x52653A9091b5d5021bed06c5118D24b23620c529 |grep MPE)
test ${MPE_BALANCE##*:} = $1
}

EXPIRATION0=$((`snet channel block-number` + 100))
EXPIRATION1=$((`snet channel block-number` + 100000))
EXPIRATION2=$((`snet channel block-number` + 100000))

snet channel open-init-metadata testo group0 1 $EXPIRATION0 -yq      #channe id  =0

# add second endpoint to metadata (in order to test case with two endpoints in metadata)
snet service metadata-add-endpoints group0 localhost:50051

# formally we will have two open chanels (channnel_id = 1,2) for the same group (testo/group0)
snet channel open-init-metadata testo group0 1 $EXPIRATION1 -yq --open-new-anyway   #channel id =1
snet channel open-init-metadata testo group0 1 $EXPIRATION2 -yq --open-new-anyway   #channel id =2

#low level equivalent to "snet client call testo tests0 classify {}"
snet --print-traceback  client  call-lowlevel testo tests group0 0 0 10000 classify {}
# should fail because nonce is incorect
snet client call-lowlevel testo tests group0 0 1 20000 classify {} && exit 1 || echo "fail as expected"
# should fail because amount is incorect
snet client call-lowlevel testo tests group0  0 0 10000 classify {} && exit 1 || echo "fail as expected"
snet client call testo tests group0  classify {} --save-response response.pb  --channel-id 1 --endpoint http://127.0.0.1:50051 -y
snet client call testo tests group0  classify {} --save-field binary_field out.bin  --channel-id 2 --endpoint http://localhost:50051 -y
snet client call testo tests group0  classify {} --save-field predictions out.txt --channel-id 2 -y
rm -f response.pb out.bin out.txt
snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
assert_balance 0.0004
snet client call testo tests group0 classify {} -y  --channel-id 0
snet client call testo tests group0 classify {} -y  --channel-id 1
snet client  get-channel-state 0 http://localhost:50051
snet client  get-channel-state 1 http://127.0.0.1:50051

# low level equivalent to "snet client call testo tests1 classify {} --channel-id 1"
snet client call-lowlevel testo tests group0 1 1 20000 classify {}

snet client call testo tests group0 classify {} --channel-id 2 -y

#only channel 0 should be claimed
snet treasurer claim-expired --expiration-threshold 1000 --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
assert_balance 0.0005
snet treasurer claim 1 2 --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
assert_balance 0.0008

echo y | snet client call testo tests group0 classify {} --channel-id 0
snet client call testo tests group0 classify {} --channel-id 0 -y
snet client call testo tests group0 classify {} --channel-id 1 -y
snet client call testo tests group0 classify {} --channel-id 2 -y

# we will start claim of all channels but will not write then to blockchain
echo n | snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 && exit 1 || echo "fail as expected"
assert_balance 0.0008

snet client call testo tests group0 classify {} --channel-id 1 -y
snet client call testo tests group0 classify {} --channel-id 2 -y

# and now we should claim everything (including pending payments)
snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
assert_balance 0.0014

kill $DAEMON
