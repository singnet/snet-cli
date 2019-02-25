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

snet client call testo tests classify {} -y

rm -rf ~/.snet/mpe_client

snet client call testo tests classify {} -y
snet client call testo tests classify {} -y --skip-update-check

# we will corrupt initialized channel
rm -rf ~/.snet/mpe_client/*/testo/tests/service/*py

# in the current version snet-cli cannot detect this problem, so it should fail
# and it is ok, because it shoudn't update service at each call
snet client call testo tests classify {} -y && exit 1 || echo "fail as expected"

snet service metadata-add-endpoints localhost:50051

# this should still fail because we skip registry check
snet client call testo tests classify {} -y --skip-update-check && exit 1 || echo "fail as expected"

snet service update-metadata testo tests -yq

# no snet-cli should automatically update service, because metadataURI has changed
snet client call testo tests classify {} -y

# multiply payment groups case
# multiply payment groups case
snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529  --fixed-price 0.0001 --endpoints 127.0.0.1:50051 --group-name group1
snet service metadata-add-group group2 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata-add-endpoints localhost:50051 --group-name group2
snet service publish testo tests2 -y -q
snet client call testo tests2 classify {} -y --group-name group2 && exit 1 || echo "fail as expected"
snet channel open-init testo tests2 1 +10days -yq --group-name group2
snet client call testo tests2 classify {} -y --group-name group2


rm -rf ~/.snet/mpe_client


kill $DAEMON

