snet session

# service side

#should fail (not existed directory)
snet service metadata-init ./bad_dir/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1 && exit 1 || echo "fail as expected"

#should fail (directory doesn't contain any *.proto files)
snet service metadata-init ./ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1 && exit 1 || echo "fail as expected"

# happy flow
snet service metadata-init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1
jq .model_ipfs_hash=1 service_metadata.json > tmp.txt
mv -f tmp.txt service_metadata.json
snet service metadata-set-model ./service_spec1/
snet service metadata-add-description --json '{"description_string":"string1","description_int":1,"description_dict":{"a":1,"b":"s"}}'
snet service metadata-add-description --json '{"description_string":"string1","description_int":1,"description_dict":{"a":1,"b":"s"}}' --description "description" --url "http://127.0.0.1"
cat service_metadata.json | jq '.service_description.url' |grep "http://127.0.0.1"
snet service metadata-add-description --url "http://127.0.0.2"
cat service_metadata.json | jq '.service_description.url' |grep "http://127.0.0.2"
snet service metadata-add-description --json '{"description":"s"}' --description "description" && exit 1 || echo "fail as expected"
snet service metadata-add-description --json '{"url":"http://127.0.0.1"}' --url "http://127.0.0.2" && exit 1 || echo "fail as expected"


snet service metadata-add-group group2 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata-add-endpoints  8.8.8.8:2020 9.8.9.8:8080 --group-name group1
snet service metadata-add-endpoints  8.8.8.8:22   1.2.3.4:8080 --group-name group2
grep "8.8.8.8:2020" service_metadata.json
snet service  metadata-remove-all-endpoints
grep "8.8.8.8:2020" service_metadata.json && exit 1 || echo "fail as expected"
snet service metadata-add-endpoints  8.8.8.8:2020 9.8.9.8:8080 --group-name group1
snet service metadata-add-endpoints  8.8.8.8:22   1.2.3.4:8080 --group-name group2
snet service metadata-update-endpoints 8.8.8.8:23456  1.2.3.4:22 --group-name group2
grep "8.8.8.8:23456" service_metadata.json
grep "8.8.8.8:2020" service_metadata.json
grep "9.8.9.8:8080" service_metadata.json
grep "8.8.8.8:22" service_metadata.json && exit 1 || echo "fail as expected"
grep "1.2.3.4:8080" service_metadata.json && exit 1 || echo "fail as expected"




snet service metadata-set-fixed-price 0.0001

# test --endpoints and --fixed-price options in 'snet service metadata-init'
snet service metadata-init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1 --fixed-price 0 --endpoints 8.8.8.8:2020 9.8.9.8:8080 --metadata-file service_metadata2.json
grep fixed_price service_metadata2.json
snet service metadata-init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service-type jsonrpc --group-name group1 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 9.8.9.8:8080 --metadata-file service_metadata2.json
grep fixed_price service_metadata2.json
grep 9.8.9.8:8080 service_metadata2.json

IPFS_HASH=$(snet service publish-in-ipfs)
ipfs cat $IPFS_HASH > service_metadata2.json

# compare service_metadata.json and service_metadata2.json
cmp <(jq -S . service_metadata.json) <(jq -S . service_metadata2.json)

snet organization create org1 --org-id testo -y -q  --gas-price fast
snet service publish testo tests -y -q  --gas-price medium
snet service update-add-tags testo tests tag1 tag2 tag3 -y -q --gas-price slow
snet service update-remove-tags testo tests tag2 tag1 -y -q  --gas-price 1000000000
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
snet account deposit 123456 -y -q
snet account transfer 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 42 -y -q
snet account withdraw 1 -y -q
snet channel open-init-metadata testo metadata-tests 42 1 --group-name group1 -y  -q
snet channel claim-timeout 0 -y -q
# we do not send transaction second time
snet channel claim-timeout 0 -y -q && exit 1 || echo "fail as expected"

snet channel extend-add 0 --expiration 10000 --amount 42 -y  -q
snet channel extend-add 0 --amount 42 -y  -q
snet channel extend-add 0 --expiration +10000blocks   -y  -q
snet channel extend-add 0 --expiration +10000days  -y  -q && exit 1 || echo "fail as expected"
snet channel extend-add 0 --expiration +10000days --force  -y  -q
snet channel extend-add 0 --expiration 57600000 --force  -y  -q && exit 1 || echo "fail as expected"

EXPIRATION1=$((`snet channel block-number` + 57600000))
snet channel extend-add 0 --expiration $EXPIRATION1 --force  --amount 0  -y  -q

snet channel open-init  testo tests 9712.1234 +14days  --group-name group2 -y -q

# test print_initialized_channels and print_all_channels. We should have channels openned for specific identity
snet channel print-initialized | grep 9712.1234
snet channel print-all-filter-sender |grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144

# we have two initilized channels one for group1 and anther for group1 (recipient=0x42A605c07EdE0E1f648aB054775D6D4E38496144)

snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529  --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --metadata-file service_metadata2.json
grep "8.8.8.8:2020" service_metadata2.json
snet service metadata-update-endpoints 8.8.8.8:2025 --metadata-file service_metadata2.json
grep "8.8.8.8:2025" service_metadata2.json
grep "8.8.8.8:2020" service_metadata2.json && exit 1 || echo "fail as expected"


snet service publish testo tests2 -y -q --metadata-file service_metadata2.json

snet channel open-init testo tests2 7234.345 1 -y  -q --signer 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB

snet channel print-initialized-filter-service testo tests2
snet channel print-initialized-filter-service testo tests2 |grep 7234.345
snet channel print-initialized-filter-service testo tests2 |grep 9712.1234 && exit 1 || echo "fail as expected"

snet channel print-initialized
snet channel print-initialized | grep 9712.1234
snet channel print-initialized | grep 7234.345

snet channel print-initialized --only-id
snet channel print-initialized --only-id | grep 7234.345 && exit 1 || echo "fail as expected"

snet channel print-initialized --filter-signer | grep 7234.345 && exit 1 || echo "fail as expected"
snet channel print-initialized --filter-signer --wallet-index 1 | grep 7234.345

snet channel  print-initialized-filter-service testo tests2
snet channel  print-initialized-filter-service testo tests2 |grep 7234.345

rm -rf ~/.snet/mpe_client/

# snet shoundn't try to open new channels. He simply should reinitilize old ones
snet channel open-init  testo tests  0 0  --group-name group1
snet channel open-init  testo tests  0 0  --group-name group2
snet channel open-init  testo tests2 0 0 --signer 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB
snet channel print-initialized  | grep 7234.345
snet channel print-initialized  | grep 9712.1234
snet channel open-init-metadata  testo tests-metadata 0 0  --group-name group2


rm -rf ~/.snet/mpe_client/
# this should open new channel instead of using old one
snet channel open-init  testo tests  1 1  --group-name group2 --open-new-anyway -yq
snet channel print-initialized  | grep 9712.1234 && exit 1 || echo "fail as expected"

rm -rf ~/.snet/mpe_client/


snet channel print-all-filter-sender
snet channel print-all-filter-sender | grep 0x52653A9091b5d5021bed06c5118D24b23620c529

snet channel print-all-filter-recipient | grep 0x52653A9091b5d5021bed06c5118D24b23620c529 && exit 1 || echo "fail as expected"
snet channel print-all-filter-recipient --wallet-index 9 |grep 0x52653A9091b5d5021bed06c5118D24b23620c529
snet channel print-all-filter-recipient --recipient 0x52653A9091b5d5021bed06c5118D24b23620c529 |grep 0x52653A9091b5d5021bed06c5118D24b23620c529

snet channel print-all-filter-group testo tests2 | grep 0x52653A9091b5d5021bed06c5118D24b23620c529
snet channel print-all-filter-group testo tests2 | grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144 && exit 1 || echo "fail as expected"

snet channel print-all-filter-group testo tests --group-name group2 |grep 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18

snet channel print-all-filter-group-sender testo tests2 | grep 0x52653A9091b5d5021bed06c5118D24b23620c529
snet channel print-all-filter-group-sender testo tests2 | grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144 && exit 1 || echo "fail as expected"

# should fail because of wrong groupId
snet channel init-metadata testo metadata-tests 0 --metadata-file service_metadata2.json  && exit 1 || echo "fail as expected"
snet channel init testo tests2 1 && exit 1 || echo "fail as expected"

snet channel init-metadata testo metadata-tests 0
snet channel init testo tests 1
snet channel print-initialized
snet channel print-all-filter-sender
snet service delete testo tests -y -q
snet organization list-services testo

# open channel with sender=signer=0x32267d505B1901236508DcDa64C1D0d5B9DF639a

snet account transfer 0x32267d505B1901236508DcDa64C1D0d5B9DF639a 1 -y -q
snet channel open-init testo tests2 1 314156700003452 --force -y  -q --wallet-index 3
snet channel print-all-filter-sender --sender 0x32267d505B1901236508DcDa64C1D0d5B9DF639a |grep 314156700003452
snet channel print-all-filter-sender |grep 314156700003452 && exit 1 || echo "fail as expected"

snet channel print-all-filter-group-sender testo tests2 --sender 0x32267d505B1901236508DcDa64C1D0d5B9DF639a |grep 314156700003452

# test migration to different network

# get service metadata from registry and set mpe_address to wrong value
snet service print-metadata  testo tests2 | jq '.mpe_address = "0x52653A9091b5d5021bed06c5118D24b23620c529"' > service_metadata.json

# this should fail because of wrong mpe_address
snet service publish-in-ipfs && exit 1 || echo "fail as expected"

snet service publish-in-ipfs --multipartyescrow-at 0x52653A9091b5d5021bed06c5118D24b23620c529
snet service publish-in-ipfs && exit 1 || echo "fail as expected"
snet service publish-in-ipfs --update-mpe-address
snet service publish-in-ipfs

snet service print-metadata  testo tests2 | jq '.mpe_address = "0x52653A9091b5d5021bed06c5118D24b23620c529"' > service_metadata.json

# this should fail because of wrong mpe_address
snet service publish testo tests4 && exit 1 || echo "fail as expected"

snet service publish testo tests4 --multipartyescrow-at 0x52653A9091b5d5021bed06c5118D24b23620c529 -yq
snet service publish testo tests5 -yq && exit 1 || echo "fail as expected"
snet service publish testo tests6 --update-mpe-address -yq
snet service publish testo tests7 -yq

# test snet service update-metadata
snet service metadata-add-group group2 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata-add-endpoints 8.8.8.8:22  1.2.3.4:8080 --group-name group2
snet service update-metadata testo tests7 -y
