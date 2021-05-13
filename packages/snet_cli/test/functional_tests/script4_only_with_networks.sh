# We try to get config address from the differnt sources.
# The order of priorioty is following:
# - command line argument (at or <contract_name>_at)
# - current session configuration (current_<contract_name>_at)
# - networks/*json

# In this test we check this priority

rm -rf ../../snet/snet_cli/resources/contracts/networks/*.json

#unset addresses
snet unset current_singularitynettoken_at || echo "could fail if hasn't been set (it is ok)"
snet unset current_registry_at || echo "could fail if hasn't been set (it is ok)"
snet unset current_multipartyescrow_at || echo "could fail if hasn't been set (it is ok)"
snet session
# this should fail without addresses
snet account balance && exit 1 || echo "fail as expected"
snet --print-traceback organization metadata-init org1 testo individual && exit 1 || echo "fail as expected"
snet organization create testo testo -y -q && exit 1 || echo "fail as expected"

# set networks
echo '{"829257324":{"events":{},"links":{},"address":"0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e","transactionHash":""}}' >../../snet/snet_cli/resources/contracts/networks/MultiPartyEscrow.json
echo '{"829257324":{"events":{},"links":{},"address":"0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2","transactionHash":""}}' >../../snet/snet_cli/resources/contracts/networks/Registry.json
echo '{"829257324":{"events":{},"links":{},"address":"0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14","transactionHash":""}}' >../../snet/snet_cli/resources/contracts/networks/SingularityNetToken.json

# this should work
snet account balance
snet --print-traceback organization metadata-init org1 testo individual
snet --print-traceback organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 5.5.6.7:8089
snet --print-traceback organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 1.2.1.1:8089
snet organization create testo -y -q
snet organization delete testo -y -q

# this should fail (addresses are INVALID)
snet organization create testo -y -q --registry-at 0x1e74fefa82e83e0964f0d9f53c68e03f7298a8b2 && exit 1 || echo "fail as expected"
snet account balance --snt 0x1e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e && exit 1 || echo "fail as expected"

# set INVALID addresses
snet set current_singularitynettoken_at 0x1e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14
snet set current_registry_at 0x1e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet set current_multipartyescrow_at 0x1c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e

# this should fail because INVALID address
snet account balance && exit 1 || echo "fail as expected"
snet --print-traceback organization metadata-init org1 testo individual && exit 1 || echo "fail as expected"
snet organization create testo -y -q && exit 1 || echo "fail as expected"

# this should work because command line has more priority
snet account balance --snt 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet --print-traceback organization metadata-init org1 testo individual --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet --print-traceback organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 5.5.6.7:8089 --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet --print-traceback organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 1.2.1.1:8089 --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2

snet organization create testo -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet organization delete testo -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2

# set INVALID networks
echo '{"829257324":{"events":{},"links":{},"address":"0x1c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e","transactionHash":""}}' >../../snet/snet_cli/resources/contracts/networks/MultiPartyEscrow.json
echo '{"829257324":{"events":{},"links":{},"address":"0x1e74fefa82e83e0964f0d9f53c68e03f7298a8b2","transactionHash":""}}' >../../snet/snet_cli/resources/contracts/networks/Registry.json
echo '{"829257324":{"events":{},"links":{},"address":"0x1e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14","transactionHash":""}}' >../../snet/snet_cli/resources/contracts/networks/SingularityNetToken.json

# this should fail (because addresses in networks are invalid )
snet account balance && exit 1 || echo "fail as expected"
snet --print-traceback organization metadata-init org1 testo individual && exit 1 || echo "fail as expected"
snet organization create testo -y -q && exit 1 || echo "fail as expected"

# set VALID session
snet set current_singularitynettoken_at 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14
snet set current_registry_at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet set current_multipartyescrow_at 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e

# this should work
snet account balance
snet --print-traceback organization metadata-init org1 testo individual
snet --print-traceback organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 5.5.6.7:8089
snet --print-traceback organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 1.2.1.1:8089
snet organization create testo -y -q
snet organization delete testo -y -q

# set INVALID addresses
snet set current_singularitynettoken_at 0x1e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14
snet set current_registry_at 0x1e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet set current_multipartyescrow_at 0x1c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e

# this should fail (because addresses in networks are invalid )
snet account balance && exit 1 || echo "fail as expected"
snet --print-traceback organization metadata-init org1 testo individual && exit 1 || echo "fail as expected"
snet organization create testo -y -q && exit 1 || echo "fail as expected"

# this should work because command line has more priority
snet account balance --snt 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14 --mpe 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e
snet --print-traceback organization metadata-init org1 testo individual --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet --print-traceback organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 5.5.6.7:8089 --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet --print-traceback organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 1.2.1.1:8089 --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet organization create testo -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet organization delete testo -y -q --registry-at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
