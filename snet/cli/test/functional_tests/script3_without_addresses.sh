# service side
# check how snet-cli works if we pass contract address via command line interface

# remove networks
rm -rf ../../snet/snet_cli/resources/contracts/networks/*.json

#unset addresses
snet unset current_singularitynettoken_at || echo "could fail if hasn't been set (it is ok)"
snet unset current_registry_at || echo "could fail if hasn't been set (it is ok)"
snet unset current_multipartyescrow_at || echo "could fail if hasn't been set (it is ok)"

# now snet-cli will work only if we pass contract addresses as commandline arguments

# this should fail without addresses
snet account balance && exit 1 || echo "fail as expected"
snet organization create testo --org-id testo -y -q && exit 1 || echo "fail as expected"

snet --print-traceback organization metadata-init org1 testo individual --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet --print-traceback organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 5.5.6.7:8089
snet --print-traceback organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 1.2.1.1:8089
snet --print-traceback organization create testo -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2

snet service metadata-init ./service_spec1/ ExampleService --encoding json --service-type jsonrpc --group-name group1 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet service metadata-add-group group2
snet service metadata-add-endpoints group1 8.8.8.8:2020 9.8.9.8:8080
snet service metadata-add-endpoints group2 8.8.8.8:22 1.2.3.4:8080
snet service metadata-set-fixed-price group1 0.0001
snet service metadata-set-fixed-price group2 0.0001

snet service metadata-add-tags tag1 tag2 tag3
grep "tag1" service_metadata.json
grep "tag2" service_metadata.json
grep "tag3" service_metadata.json
grep "tag4" service_metadata.json && exit 1 || echo "fail as expected"

snet service metadata-remove-tags tag2 tag1
grep "tag2" service_metadata.json && exit 1 || echo "fail as expected"
grep "tag1" service_metadata.json && exit 1 || echo "fail as expected"
grep "tag3" service_metadata.json

IPFS_HASH=$(snet service publish-in-ipfs --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e)
ipfs cat $IPFS_HASH >service_metadata2.json

# compare service_metadata.json and service_metadata2.json
cmp <(jq -S . service_metadata.json) <(jq -S . service_metadata2.json)

snet service publish testo tests -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet service update-add-tags testo tests tag1 tag2 tag3 -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet service update-remove-tags testo tests tag2 tag1 -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet service print-tags testo tests --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet organization list --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
# it should have only tag3 now
cmp <(echo "tag3") <(snet service print-tags testo tests --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2)

snet service print-metadata testo tests --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2 | grep -v "We must check that hash in IPFS is correct" >service_metadata3.json

# compare service_metadata.json and service_metadata3.json
cmp <(jq -S . service_metadata.json) <(jq -S . service_metadata3.json)

# client side
snet account balance --snt 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet account deposit 12345 -y -q --snt 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet account transfer 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 42 -y -q --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet account withdraw 1 -y -q --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet channel open-init-metadata testo group1 42 1 -y -q --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e --registry 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet channel claim-timeout 0 -y -q --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet channel extend-add 0 --expiration 10000 --amount 42 -y -q --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet channel open-init testo group2 1 1000000 -y -q --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e --registry 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet channel print-initialized --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e --registry 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet channel print-all-filter-sender --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
rm -rf ~/.snet/mpe_client/
snet channel init-metadata testo group1 0 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e --registry 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet channel init testo group1 1 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e --registry 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet channel print-initialized --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e --registry 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet channel print-all-filter-sender --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet service delete testo tests -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet organization list-services testo --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
