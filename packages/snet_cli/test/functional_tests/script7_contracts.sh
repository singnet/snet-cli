# Test "snet contracts"

snet contract Registry --at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2 createOrganization ExampleOrganization1 ExampleOrganization1 '["0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB"]' --transact -y
snet contract Registry createOrganization ExampleOrganization2 ExampleOrganization2 '["0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB","0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18"]' --transact -y
snet organization list 2>&1 | grep ExampleOrganization1
snet organization list 2>&1 | grep ExampleOrganization2

# organization ExampleOrganization2 should alread have two given members
snet organization add-members ExampleOrganization2 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB,0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 -y 2>&1 | grep "No member was added"

# deposit 1000000 cogs to MPE from the first address (0x592E3C0f3B038A0D673F19a18a773F993d4b2610)
snet contract SingularityNetToken --at 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14 approve 0x5C7a4290F6F8FF64c69eEffDFAFc8644A4Ec3a4E 1000000 --transact -y
snet contract MultiPartyEscrow --at 0x5C7a4290F6F8FF64c69eEffDFAFc8644A4Ec3a4E  deposit  1000000 --transact -y

# deposit 1000000 cogs to MPE from the first address (0x592E3C0f3B038A0D673F19a18a773F993d4b2610)
snet contract SingularityNetToken approve 0x5C7a4290F6F8FF64c69eEffDFAFc8644A4Ec3a4E 1000000 --transact -y
snet contract MultiPartyEscrow    deposit  1000000 --transact -y

# check balance of the First account in MPE (it should be 2000000 cogs)
REZ=`snet contract  MultiPartyEscrow --at 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e balances 0x592E3C0f3B038A0D673F19a18a773F993d4b2610`
test $REZ = 2000000

# We set expiration as current_block - 1
EXPIRATION=$((`snet channel block-number` - 1))
snet contract MultiPartyEscrow --at 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e openChannel  0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 0 420000 $EXPIRATION --transact -y

REZ=`snet contract MultiPartyEscrow nextChannelId`
test $REZ = 1

#We can immediately claim timeout because expiration was set in the past
snet contract MultiPartyEscrow --at 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e channelClaimTimeout 0 --transact -y