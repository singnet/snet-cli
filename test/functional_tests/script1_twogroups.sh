# service side

#should fail (not existed directory)
snet service metadata-init ./bad_dir/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1 && exit 1 || echo "fail as expected"

#should fail (directory doesn't contain any *.proto files)
snet service metadata-init ./ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1 && exit 1 || echo "fail as expected"

# happy flow
snet service metadata-init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1
snet service metadata-add-group group2 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata-add-endpoints  8.8.8.8:2020 9.8.9.8:8080 --group-name group1
snet service metadata-add-endpoints  8.8.8.8:22   1.2.3.4:8080 --group-name group2
snet service metadata-set-fixed-price 0.0001

# test --endpoints and --fixed-price options in 'snet service metadata-init'
snet service metadata-init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 9.8.9.8:8080 --metadata-file service_metadata2.json
grep fixed_price service_metadata2.json
grep 9.8.9.8:8080 service_metadata2.json

IPFS_HASH=$(snet service publish-in-ipfs)
ipfs cat $IPFS_HASH > service_metadata2.json

# compare service_metadata.json and service_metadata2.json
cmp <(jq -S . service_metadata.json) <(jq -S . service_metadata2.json)

snet organization create org1 --org-id testo -y -q
snet service publish testo tests -y -q
snet service update-add-tags testo tests tag1 tag2 tag3 -y -q
snet service update-remove-tags testo tests tag2 tag1 -y -q
snet service print-tags  testo tests

# it should have only tag3 now
cmp <(echo "tag3") <(snet service print-tags testo tests)

snet service print-metadata  testo tests > service_metadata3.json

# compare service_metadata.json and service_metadata3.json
cmp <(jq -S . service_metadata.json) <(jq -S . service_metadata3.json)

# test get_api_registry and
snet service get-api-registry testo tests _d1
snet service get-api-metadata --metadata-file service_metadata3.json _d2

# as usual, by default it is metatada_file=service_metadata.json
snet service get-api-metadata _d3

cmp ./service_spec1/ExampleService.proto _d1/ExampleService.proto
cmp ./service_spec1/ExampleService.proto _d2/ExampleService.proto
cmp ./service_spec1/ExampleService.proto _d3/ExampleService.proto

rm -r _d1 _d2 _d3

# client side
snet account balance
snet account deposit 12345 -y -q
snet account transfer 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 42 -y -q
snet account withdraw 1 -y -q
snet channel open-init-metadata 42 1 --group-name group1 -y  -q
snet channel claim-timeout 0 -y -q
# we do not send transaction second time
snet channel claim-timeout 0 -y -q && exit 1 || echo "fail as expected"

snet channel extend-add 0 --expiration 10000 --amount 42 -y  -q
snet channel open-init  testo tests 1 1000000  --group-name group2 -y -q

# test print_initialized_channels and print_all_channels. We should have channels openned for specific identity
snet channel print-initialized | grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144
snet channel print-all-filter-sender |grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144

rm -rf ~/.snet/mpe_client/
snet channel init-metadata 0
snet channel init testo tests 1
snet channel print-initialized
snet channel print-all-filter-sender
snet service delete testo tests -y -q
snet organization list-services testo
