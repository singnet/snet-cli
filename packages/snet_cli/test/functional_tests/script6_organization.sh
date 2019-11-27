# Test "snet organization"

snet organization metadata-init org1 testo
snet organization add-group group1 0x42A605c07EdE0E1f648aB054775D6D4E38496144 5.5.6.7:8089
snet organization add-group group2 0x42A605c07EdE0E1f648aB054775D6D4E38496144 1.2.1.1:8089
snet organization create test0 -y -q

# fail to create organization with the same id
snet organization create test0 -y -q && exit 1 || echo "fail as expected"

## check if this feature is required  --org-id and --auto are mutually exclusive
snet organization create test1 --org-id test1 --auto -y -q && exit 1 || echo "fail as expected"

## create organization with random id
snet organization create test0 --auto -y -q && exit 1 || echo "fail as expected"

snet organization create test1 --members 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB -y -q
snet organization create test2 --members 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB,0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 -y -q
snet organization add-members test2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a -y
snet organization add-members test2 0x5c1011aB3C7f46EC5E78073D61DF6d002983F04a,0x42A605c07EdE0E1f648aB054775D6D4E38496144 -y
snet organization add-members test2 0x5c1011aB3C7f46EC5E78073D61DF6d002983F04a,0x42A605c07EdE0E1f648aB054775D6D4E38496144 -y | grep "No member was added"
snet organization add-members test2 0x5c1011aB3C7f46EC5E78073D61DF6d002983F04a,0x42A605c07EdE0E1f648aB054775D6D4E38496144,0xc990EEAad8c943E3C6bA4cbcd8a54a949Fb83f78 -y

snet --print-traceback service metadata-init ./service_spec1/ ExampleService --encoding json --service-type jsonrpc --group-name group1
snet service metadata-add-endpoints group1 8.8.8.8:22 1.2.3.4:8080
snet service metadata-set-fixed-price group1 0.0001
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


snet --print-traceback organization metadata-add-assets ./service_spec1/test hero_image
result=$(< organization_metadata.json jq '.assets.hero_image')
test $result = '"QmWQhwwnvK4YHvEarEguTDhz8o2kwvyfPhv5favs1VS4xm/test"' && echo "add asset with single value  test case passed " || exit 1

#remove assets
snet --print-traceback organization metadata-remove-assets hero_image
test "$(< organization_metadata.json jq '.assets.hero_image')" = '""' && echo "metadata-remove-assets  test case passed " || exit 1

snet --print-traceback organization metadata-remove-all-assets
test "$(< organization_metadata.json jq '.assets')" = '{}' && echo "metadata-remove-all-assets test case passed " || exit 1

# description test
snet --print-traceback organization metadata-add-description "this is the dummy description of my org"
test "$(< organization_metadata.json jq '.description')" = '"this is the dummy description of my org"' || exit 1

# contacts test
# add contact
snet --print-traceback organization metadata-add-contact support --email dummy@dummy.io --phone 1234567890
(test "$(< organization_metadata.json jq '.contacts | length')" = 1 \
&& test "$(< organization_metadata.json jq '.contacts[0].contact_type')" = '"support"' \
&& test "$(< organization_metadata.json jq '.contacts[0].phone')" = '"1234567890"' \
&& test "$(< organization_metadata.json jq '.contacts[0].email_id')" = '"dummy@dummy.io"' \
&& echo "passed") || exit 1

# add contact without email and phone
test "$(snet --print-traceback organization metadata-add-contact support)" = "email and phone both can not be empty" \
|| exit 1

# remove contact by type
snet --print-traceback organization metadata-add-contact support --email support@dummy.io --phone 0987654321
snet --print-traceback organization metadata-add-contact dummy --email dummy@dummy.io --phone 6789012345
snet --print-traceback organization metadata-remove-contacts dummy
test "$(< organization_metadata.json jq '.contacts | length')" = 2 && echo "passed" || exit 1

# remove all contacts
snet --print-traceback organization metadata-remove-all-contacts
test "$(< organization_metadata.json jq '.contacts | length')" = 0 && echo "passed" || exit 1


snet organization change-owner test2 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB -y
snet organization change-owner test2 0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB -y && exit 1 || echo "fail as expected"
snet organization add-members test2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a -y && exit 1 || echo "fail as expected"

# this should work because owner is the second account
snet organization add-members test2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a --wallet-index 1 -y

snet organization delete test2 -y && exit 1 || echo "fail as expected"

snet organization delete test2 --wallet-index 1 -y

snet organization info test2 || echo "fail as expected"
