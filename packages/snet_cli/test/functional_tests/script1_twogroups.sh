snet session

# service side

#should fail (not existed directory)
snet service metadata-init ./bad_dir/ ExampleService --encoding json --service-type jsonrpc --group-name group1 && exit 1 || echo "fail as expected"

#should fail (directory doesn't contain any *.proto files)
snet service metadata-init ./ ExampleService --encoding json --service-type jsonrpc --group-name group1 && exit 1 || echo "fail as expected"

# happy flow
snet --print-traceback service metadata-init ./service_spec1/ ExampleService --encoding json --service-type jsonrpc --group-name group1
jq .model_ipfs_hash=1 service_metadata.json >tmp.txt
mv -f tmp.txt service_metadata.json
snet service metadata-set-model ./service_spec1/
snet service metadata-add-description --json '{"description_string":"string1","description_int":1,"description_dict":{"a":1,"b":"s"}}'
snet service metadata-add-description --json '{"description_string":"string1","description_int":1,"description_dict":{"a":1,"b":"s"}}' --description "description" --url "http://127.0.0.1"
cat service_metadata.json | jq '.service_description.url' | grep "http://127.0.0.1"
snet service metadata-add-description --url "http://127.0.0.2"
cat service_metadata.json | jq '.service_description.url' | grep "http://127.0.0.2"
snet service metadata-add-description --json '{"description":"s"}' --description "description" && exit 1 || echo "fail as expected"
snet service metadata-add-description --json '{"url":"http://127.0.0.1"}' --url "http://127.0.0.2" && exit 1 || echo "fail as expected"

#seconf argument is group_id should be removed
snet service metadata-add-group group2
snet service metadata-add-endpoints group1 8.8.8.8:2020 9.8.9.8:8080
snet service metadata-add-endpoints group2 8.8.8.8:22 1.2.3.4:8080
grep "8.8.8.8:2020" service_metadata.json
snet service metadata-remove-all-endpoints group2
grep "8.8.8.8:22" service_metadata.json && exit 1 || echo "fail as expected"
snet service metadata-remove-all-endpoints group1
snet service metadata-add-endpoints group1 8.8.8.8:2020 9.8.9.8:8080
snet service metadata-add-endpoints group2 8.8.8.8:22 1.2.3.4:8080
snet --print-traceback service metadata-update-endpoints group2 8.8.8.8:23456 1.2.3.4:22
grep "8.8.8.8:23456" service_metadata.json
grep "8.8.8.8:2020" service_metadata.json
grep "9.8.9.8:8080" service_metadata.json
grep "8.8.8.8:22" service_metadata.json && exit 1 || echo "fail as expected"
grep "1.2.3.4:8080" service_metadata.json && exit 1 || echo "fail as expected"

snet service metadata-set-fixed-price group1 0.0001

# test --endpoints and --fixed-price options in 'snet service metadata-init'
snet --print-traceback service metadata-init ./service_spec1/ ExampleService --encoding json --service-type jsonrpc --group-name group1 --fixed-price 0 --endpoints 8.8.8.8:2020 9.8.9.8:8080 --metadata-file service_metadata2.json
grep fixed_price service_metadata2.json
snet service metadata-init ./service_spec1/ ExampleService --encoding json --service-type jsonrpc --group-name group1 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 9.8.9.8:8080 --metadata-file service_metadata2.json
grep fixed_price service_metadata2.json
grep 9.8.9.8:8080 service_metadata2.json

IPFS_HASH=$(snet service publish-in-ipfs)
echo $IPFS_HASH
ipfs cat $IPFS_HASH >service_metadata2.json

# compare service_metadata.json and service_metadata2.json
cmp <(jq -S . service_metadata.json) <(jq -S . service_metadata2.json)
snet organization metadata-init org1 testo individual
grep org1 organization_metadata.json
snet organization create testo && exit 1 || echo "fail as expected"
#
snet --print-traceback organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 5.5.6.7:8089
snet --print-traceback organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 1.2.1.1:8089
grep 5.5.6.7 organization_metadata.json
grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144 organization_metadata.json
grep 5.5.6.7:8089 organization_metadata.json
snet --print-traceback organization create testo -y
snet organization print-metadata org1 testo >organization_metadata_print.json

snet service metadata-add-tags tag1 tag2 tag3
grep "tag1" service_metadata.json
grep "tag2" service_metadata.json
grep "tag3" service_metadata.json
grep "tag4" service_metadata.json && exit 1 || echo "fail as expected"

snet service metadata-remove-tags tag2 tag1
grep "tag2" service_metadata.json && exit 1 || echo "fail as expected"
grep "tag1" service_metadata.json && exit 1 || echo "fail as expected"
grep "tag3" service_metadata.json

snet service publish testo tests -y -q --gas-price medium
snet service update-add-tags testo tests tag1 tag2 tag3 -y -q --gas-price slow
snet service update-remove-tags testo tests tag2 tag1 -y -q --gas-price 1000000000
snet service print-tags testo tests

# it should have only tag3 now
cmp <(echo "tag3") <(snet service print-tags testo tests)

snet service print-metadata testo tests >service_metadata3.json

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

#open channel usig org and group
snet --print-traceback channel open-init-metadata testo group1 42 1 -y -q
snet channel print-initialized
snet channel claim-timeout 0 -y -q
snet channel print-initialized
# we do not send transaction second time
snet channel claim-timeout 0 -y -q && exit 1 || echo "fail as expected"

snet channel extend-add 0 --expiration 10000 --amount 42 -y -q
snet channel print-initialized
snet channel extend-add 0 --amount 42 -y -q
snet channel print-initialized
snet channel extend-add 0 --expiration +10000blocks -y -q
snet channel extend-add 0 --expiration +10000days -y -q && exit 1 || echo "fail as expected"
snet channel extend-add 0 --expiration +10000days --force -y -q
snet channel extend-add 0 --expiration 57600000 --force -y -q && exit 1 || echo "fail as expected"

EXPIRATION1=$(($(snet channel block-number) + 57600000))
snet channel extend-add 0 --expiration $EXPIRATION1 --force --amount 0 -y -q

snet channel open-init testo group1 9712.1234 +14days -y -q

# test print_initialized_channels and print_all_channels. We should have channels openned for specific identity
snet channel print-initialized
snet --print-traceback channel print-initialized | grep 84
snet channel print-all-filter-sender | grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144

# we have two initilized channels one for group1 and anther for group1 (recipient=0x42A605c07EdE0E1f648aB054775D6D4E38496144)

snet --print-traceback service metadata-init ./service_spec1/ ExampleService --group-name group2 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --metadata-file service_metadata2.json
grep "8.8.8.8:2020" service_metadata2.json
snet service metadata-update-endpoints group2 8.8.8.8:2025 --metadata-file service_metadata2.json
grep "8.8.8.8:2025" service_metadata2.json
grep "8.8.8.8:2020" service_metadata2.json && exit 1 || echo "fail as expected"

snet service publish testo tests2 -y -q --metadata-file service_metadata2.json

snet channel open-init testo group2 7234.345 1 -y -q --signer 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB

snet --print-traceback channel print-initialized-filter-org testo group2
snet channel print-initialized-filter-org testo group2 | grep 7234.345
snet channel print-initialized-filter-org testo group2 | grep 9712.1234 && exit 1 || echo "fail as expected"

snet channel print-initialized
snet channel print-initialized | grep 84
snet channel print-initialized | grep 7234.345

snet channel print-initialized --only-id
snet channel print-initialized --only-id | grep 7234.345 && exit 1 || echo "fail as expected"

snet channel print-initialized --filter-signer | grep 7234.345 && exit 1 || echo "fail as expected"
snet channel print-initialized --filter-signer --wallet-index 1 | grep 7234.345

snet channel print-initialized-filter-org testo group2
snet channel print-initialized-filter-org testo group2 | grep 7234.345

rm -rf ~/.snet/mpe_client/

# snet shoundn't try to open new channels. He simply should reinitilize old ones
snet channel open-init testo group1 0 0 -y -q
snet channel open-init testo group2 0 0 -y -q
snet channel open-init testo group2 0 0 --signer 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB -y -q
snet channel print-initialized | grep 7234.345
snet channel print-initialized | grep 84
snet channel open-init-metadata testo group2 0 0

rm -rf ~/.snet/mpe_client/
# this should open new channel instead of using old one
snet channel open-init testo group2 111222 1 --open-new-anyway -yq
snet channel print-initialized | grep 9712.1234 && exit 1 || echo "fail as expected"
snet channel print-initialized-filter-org testo group2 | grep 111222

rm -rf ~/.snet/mpe_client/

snet --print-traceback channel print-all-filter-group testo group2
snet channel print-all-filter-sender
snet channel print-all-filter-recipient

#Uncomment this when all testing is done
#snet channel print-all-filter-sender | grep  0x42A605c07EdE0E1f648aB054775D6D4E38496144
#
#snet channel print-all-filter-recipient | grep 0x52653A9091b5d5021bed06c5118D24b23620c529 && exit 1 || echo "fail as expected"
#snet channel print-all-filter-recipient --wallet-index 9 |grep 0x52653A9091b5d5021bed06c5118D24b23620c529
#snet channel print-all-filter-recipient --recipient 0x52653A9091b5d5021bed06c5118D24b23620c529 |grep 0x52653A9091b5d5021bed06c5118D24b23620c529
#
#snet channel print-all-filter-group testo group2 | grep 0x52653A9091b5d5021bed06c5118D24b23620c529
#snet channel print-all-filter-group testo group2 | grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144 && exit 1 || echo "fail as expected"
#
#snet channel print-all-filter-group testo group2 |grep 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
#
#snet channel print-all-filter-group-sender testo group2 | grep 0x52653A9091b5d5021bed06c5118D24b23620c529
#snet channel print-all-filter-group-sender testo group2 | grep 0x42A605c07EdE0E1f648aB054775D6D4E38496144 && exit 1 || echo "fail as expected"

# should fail because of wrong groupId
snet channel init-metadata testo metadata-tests 0 --metadata-file service_metadata2.json && exit 1 || echo "fail as expected"
snet channel init testo wrong_group_name 1 && exit 1 || echo "fail as expected"

snet --print-traceback channel init-metadata testo group1 1
snet --print-traceback channel init testo group2 1
snet channel print-initialized
snet channel print-all-filter-sender
snet service delete testo tests -y -q
snet organization list-services testo

# open channel with sender=signer=0x32267d505B1901236508DcDa64C1D0d5B9DF639a

snet account transfer 0x32267d505B1901236508DcDa64C1D0d5B9DF639a 1 -y -q
snet channel open-init testo group2 1 314156700003452 --force -y -q --wallet-index 3
snet channel print-all-filter-sender --sender 0x32267d505B1901236508DcDa64C1D0d5B9DF639a | grep 314156700003452
snet channel print-all-filter-sender | grep 314156700003452 && exit 1 || echo "fail as expected"

snet channel print-all-filter-group-sender testo group2 --sender 0x32267d505B1901236508DcDa64C1D0d5B9DF639a | grep 314156700003452
snet organization list-services testo
# test migration to different network

# get service metadata from registry and set mpe_address to wrong value
snet service print-metadata testo tests2 | jq '.mpe_address = "0x52653A9091b5d5021bed06c5118D24b23620c529"' >service_metadata.json

# this should fail because of wrong mpe_address
snet service publish-in-ipfs && exit 1 || echo "fail as expected"

snet service publish-in-ipfs --multipartyescrow-at 0x52653A9091b5d5021bed06c5118D24b23620c529
snet service publish-in-ipfs && exit 1 || echo "fail as expected"
snet service publish-in-ipfs --update-mpe-address
snet --print-traceback service publish-in-ipfs

snet --print-traceback service print-metadata testo tests2 | jq '.mpe_address = "0x52653A9091b5d5021bed06c5118D24b23620c529"' >service_metadata.json

# this should fail because of wrong mpe_address
snet service publish testo tests4 && exit 1 || echo "fail as expected"

snet --print-traceback service publish testo tests4 --multipartyescrow-at 0x52653A9091b5d5021bed06c5118D24b23620c529 -yq
snet service publish testo tests5 -yq && exit 1 || echo "fail as expected"
snet service publish testo tests6 --update-mpe-address -yq
snet service publish testo tests7 -yq

# test snet service update-metadata
snet service metadata-add-group group1
#group already added
snet service metadata-add-group group2 && exit 1 || echo "fail as expected"
snet service metadata-add-endpoints group1 8.8.8.8:22 1.2.3.4:8080
snet service update-metadata testo tests7 -y


#testcase for updating fixed price
snet --print-traceback service metadata-init ./service_spec1/ ExampleService --encoding json --service-type jsonrpc --group-name group1 --fixed-price 0.01212 --endpoints 8.8.8.8:2020 9.8.9.8:8080 --metadata-file service_metadata_fixed_price.json
grep "1212000" service_metadata_fixed_price.json
snet service metadata-set-fixed-price group1 0.2323 --metadata-file service_metadata_fixed_price.json
grep "23230000" service_metadata_fixed_price.json
