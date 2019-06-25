# Test "snet organization"

snet organization create test0 --org-id test0 -y -q

# fail to create organization with the same id
snet organization create test0 --org-id test0 -y -q && exit 1 || echo "fail as expected"

# --org-id and --auto are mutually exclusive
snet organization create test1 --org-id test1 --auto -y -q && exit 1 || echo "fail as expected"

# create organization with random id
snet organization create test0 --auto -y -q

snet organization create test1 --org-id test1 --members 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB -y -q
snet organization create test2 --org-id test2 --members 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB,0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 -y -q
snet organization add-members test2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a -y
snet organization add-members test2 0x5c1011aB3C7f46EC5E78073D61DF6d002983F04a,0x42A605c07EdE0E1f648aB054775D6D4E38496144 -y
snet organization add-members test2 0x5c1011aB3C7f46EC5E78073D61DF6d002983F04a,0x42A605c07EdE0E1f648aB054775D6D4E38496144 -y | grep "No member was added"
snet organization add-members test2 0x5c1011aB3C7f46EC5E78073D61DF6d002983F04a,0x42A605c07EdE0E1f648aB054775D6D4E38496144,0xc990EEAad8c943E3C6bA4cbcd8a54a949Fb83f78 -y

snet service metadata-init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144 --encoding json --service-type jsonrpc --group-name group1
snet service metadata-add-endpoints 8.8.8.8:22 1.2.3.4:8080
snet service metadata-set-fixed-price 0.0001
snet service publish test2 tests -y -q
snet service publish test2 tests2 -y -q
snet organization info test2

snet organization rem-members test2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a,0x5c1011aB3C7f46EC5E78073D61DF6d002983F04a -y
snet organization rem-members test2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 -y
snet organization rem-members test2 0x42A605c07EdE0E1f648aB054775D6D4E38496144,0xc990EEAad8c943E3C6bA4cbcd8a54a949Fb83f78 -y

# second time shoudn't remove
snet organization rem-members test2 0x42A605c07EdE0E1f648aB054775D6D4E38496144,0xc990EEAad8c943E3C6bA4cbcd8a54a949Fb83f78 -y 2>&1 | grep "No member was removed"

snet organization list
snet organization list-org-names
# test2 should be found here
snet organization list-my | grep test2
snet organization info test2

# change test2 organization name to NEW_TEST2_NAME
snet organization change-name test2 NEW_TEST2_NAME -y
snet organization change-name test2 NEW_TEST2_NAME -y && exit 1 || echo "fail as expected"
# change test2 organization name back to test2
snet organization change-name test2 test2 -y

snet organization change-owner test2 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB -y
snet organization change-owner test2 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB -y && exit 1 || echo "fail as expected"
snet organization add-members test2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a -y && exit 1 || echo "fail as expected"

# this should work because owner is the second account
snet organization add-members test2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a --wallet-index 1 -y

snet organization delete test2 -y && exit 1 || echo "fail as expected"

snet organization delete test2 --wallet-index 1 -y

snet organization info test2 || echo "fail as expected"
