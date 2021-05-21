snet organization metadata-init org1 testo individual
snet organization add-group group1 0x52653A9091b5d5021bed06c5118D24b23620c529 5.5.6.7:8089
snet organization add-group group2 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 1.2.1.1:8089
snet organization create test0 -y -q

snet service metadata-init ./service_spec1/ ExampleService --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --group-name group1

snet organization create testo -y -q
snet service publish testo tests -y -q

snet account balance
snet account deposit 100000000 -yq

snet channel open-init testo group1 123.123 1 -yq

snet channel print-initialized | grep 123.223 && exit 1 || echo "fail as expected"

snet --print-traceback channel extend-add-for-org testo group1 --amount 0.1 --expiration 314 -yq
snet channel extend-add-for-org testo group1 --amount 0.2 -yq
snet --print-traceback channel extend-add-for-org testo group1 --expiration 315 -yq
snet channel print-initialized | grep 123.423
snet channel print-initialized | grep 315

rm -rf ~/.snet/mpe_client
snet --print-traceback channel extend-add-for-org testo group1 --amount 0.1 --expiration 315 -yq
snet channel extend-add-for-org testo group1 --amount 0.1 -yq
snet channel extend-add-for-org testo group1 --expiration 31415 -yq
snet channel print-initialized | grep 123.623
snet channel print-initialized | grep 31415

snet --print-traceback channel open-init testo group1 7777.8888 1 -yq --open-new-anyway
snet channel extend-add-for-org testo group1 --amount 0.01 --expiration 314 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-org testo group1 --amount 0.01 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-org testo group1 --expiration 31477 -yq && exit 1 || echo "fail as expected"

snet channel extend-add-for-org testo group1 --amount 0.01 --expiration 314 -yq --channel-id 1
snet channel extend-add-for-org testo group1 --amount 0.01 --channel-id 1 -yq
snet channel extend-add-for-org testo group1 --expiration 31477 -yq --channel-id 1
snet channel print-initialized | grep 7777.9088
snet channel print-initialized | grep 31477

# multiply payment groups case
#snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529  --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --group-name group2
snet service metadata-add-group group2
snet service metadata-add-endpoints group2 8.8.8.8:20202 9.10.9.8:8080

snet service update-metadata testo tests -yq

snet channel open-init testo group2 2222.33333 1 -yq

snet --print-traceback channel extend-add-for-org testo group1 --amount 0.001 --expiration 314 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-org testo group1 --amount 0.001 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-org testo group1 --expiration 4321 -yq && exit 1 || echo "fail as expected"

snet channel extend-add-for-org testo group2 --amount 0.001 --expiration 4321 -yq
snet channel extend-add-for-org testo group2 --amount 0.001 -yq
snet channel extend-add-for-org testo group2 --expiration 4321 -yq

snet channel print-initialized
snet channel print-initialized | grep 2222.33533
snet channel print-initialized | grep 4321

#reinitializing the channel use the existing chnanels.
snet channel open-init testo group2 2222.33333 1 -yq

snet channel print-initialized
snet channel extend-add-for-org testo group2 --amount 0.0001 --expiration 4444 -yq
snet channel extend-add-for-org testo group2 --amount 0.0001 -yq
snet channel extend-add-for-org testo group2 --expiration 5643 -yq
snet channel print-initialized
snet channel print-initialized | grep 2222.33553
snet channel print-initialized | grep 5643

rm -rf ~/.snet/mpe_client

snet channel extend-add-for-org testo group2 --amount 0.00001 --expiration 7654 -yq
snet channel extend-add-for-org testo group2 --amount 0.00001 -yq
snet channel extend-add-for-org testo group2 --expiration 7655 -yq
snet channel print-initialized
snet channel print-initialized | grep 2222.33555
snet channel print-initialized | grep 7655
