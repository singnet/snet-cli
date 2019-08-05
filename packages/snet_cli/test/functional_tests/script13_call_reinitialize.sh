# script13

# run daemon
cd simple_daemon
python test_simple_daemon.py &
DAEMON=$!
cd ..



snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529 --fixed-price 0.0001 --endpoints 127.0.0.1:50051  --group-name group1
snet account deposit 12345 -y -q
snet  organization metadata-init org1 testo
snet  organization add-group group1 0x52653A9091b5d5021bed06c5118D24b23620c529  127.0.0.1:50051

snet organization create testo  -y -q

snet service publish testo tests -y -q
snet --print-traceback service print-service-status testo tests
snet --print-traceback channel open-init testo group1 1 +10days -yq

snet --print-traceback client call testo tests  group1 classify {} -y

rm -rf ~/.snet/mpe_client

snet client call testo tests group1 classify {} -y
snet  --print-traceback client call testo tests group1 classify {} -y --skip-update-check

# we will corrupt initialized channel
rm -rf ~/.snet/mpe_client/*/testo/tests/service/*py
rm -rf ~/.snet/mpe_client/*/testo/channel*
# in the current version snet-cli cannot detect this problem, so it should fail
# and it is ok, because it shoudn't update service at each call
snet client call testo tests classify group1  {} -y && exit 1 || echo "fail as expected"


snet service metadata-add-endpoints group1 localhost:50051


# this should still fail because we skip registry check
snet  client call testo tests group1 classify {} -y --skip-update-check && exit 1 || echo "fail as expected"

snet service update-metadata testo tests -yq


# no snet-cli should automatically update service, because metadataURI has changed
snet --print-traceback client call testo tests group1  classify {} -y

# multiply payment groups case
# multiply payment groups case
snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529  --fixed-price 0.0001 --endpoints 127.0.0.1:50051 --group-name group1


snet  organization add-group group2 0x52653A9091b5d5021bed06c5118D24b23620c529  127.0.0.1:50051
snet organization update-metadata testo -yq
snet --print-traceback service publish testo tests2 -y -q
snet service print-service-status testo tests2
snet --print-traceback client call testo tests2  group2  classify {} -y   && exit 1 || echo "fail as expected"


snet service metadata-add-group group2 zT4oz1G2gEJ8q9Z9AqOio2wuFAkDXnTgTZ7sJhtozW0=
snet service metadata-set-fixed-price group2 0.0001
snet service  metadata-add-endpoints  group2 127.0.0.1:50051
snet service  update-metadata testo tests2 -y

snet --print-traceback channel open-init testo  group2 1 +10days -yq
snet --print-traceback client call testo tests2 group2 classify {} -y


rm -rf ~/.snet/mpe_client


kill $DAEMON

