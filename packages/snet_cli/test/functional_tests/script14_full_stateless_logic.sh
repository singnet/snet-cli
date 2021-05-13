# Test get-channel-state
# run daemon
cd simple_daemon
python test_simple_daemon.py &
DAEMON=$!
cd ..

snet service metadata-init ./service_spec1/ ExampleService --fixed-price 0.0001 --endpoints 127.0.0.1:50051 --group-name group1
snet account deposit 12345 -y -q
snet organization metadata-init org1 testo individual
snet organization add-group group1 0x52653A9091b5d5021bed06c5118D24b23620c529 127.0.0.1:50051

snet organization create testo -y -q

snet service publish testo tests -y -q
snet channel open-init testo group1 1 +10days -yq
snet channel print-initialized

test_get_channel_state() {
	MPE_BALANCE=$(snet client get-channel-state 0 localhost:50051 | grep current_unspent_amount_in_cogs)
	test ${MPE_BALANCE##*=} = $1
}

test_get_channel_state 100000000

snet client call testo tests group1 classify {} -y

test_get_channel_state 99990000

snet channel print-initialized
snet --print-traceback treasurer claim-all --endpoint localhost:50051 --wallet-index 9 -yq

test_get_channel_state 99990000

snet client call testo tests group1 classify {} -y
snet client call testo tests group1 classify {} -y

test_get_channel_state 99970000

# we will start claim of all channels but will not write them to blockchain
echo n | snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 && exit 1 || echo "fail as expected"

test_get_channel_state 99970000
snet client call testo tests group1 classify {} -y
test_get_channel_state 99960000

snet treasurer claim-all --endpoint 127.0.0.1:50051  --wallet-index 9 -yq
test_get_channel_state 99960000
snet client call testo tests group1 classify {} -y

test_get_channel_state 99950000

kill $DAEMON
