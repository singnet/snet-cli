# simple case of one group
snet service metadata-init ./service_spec1/ ExampleService  --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --group-name group1

snet organization metadata-init org1 testo
snet organization add-group group1 0x52653A9091b5d5021bed06c5118D24b23620c529 5.5.6.7:8089
snet organization add-group group2 0x52653A9091b5d5021bed06c5118D24b23620c529 1.2.1.1:8089
snet organization create testo -y -q
snet service publish testo tests -y -q

# change group_id

#snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --metadata-file service_metadata2.json
#
#snet service update-metadata testo tests --metadata-file service_metadata2.json -yq && exit 1 || echo "fail as expected"

#this has been moved to organization level
##change payment_address
#cat service_metadata.json | jq '.groups[0].payment_address = "0xc7973537517BfDeA79EE11Fa2D52584241a34dF2"' >service_metadata2.json
#snet service update-metadata testo tests --metadata-file service_metadata2.json -yq && exit 1 || echo "fail as expected"

# case with several groups
snet service metadata-init ./service_spec1/ ExampleService  --group-name group0 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 9.8.9.8:8080
snet service metadata-add-group group1 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata-add-endpoints group1 8.8.8.8:22 1.2.3.4:8080

snet service metadata-add-group group2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a
snet service metadata-add-endpoints group2 8.8.8.8:2 1.2.3.4:800

# this should be fine because we've completly removed default_group
snet service update-metadata testo tests -yq

## change group_id   wil now be grenerated by org level
#cat service_metadata.json | jq '.groups[1].group_id = "B5r64fQiiB5kvkWZDo7lXmo4i8y0chUvob5/CmfqoP4="' >service_metadata2.json
#mv -f service_metadata2.json service_metadata.json
#
#snet service update-metadata testo tests -yq && exit 1 || echo "fail as expected"

##change payment_address
#snet service print-metadata testo tests >service_metadata.json
#cat service_metadata.json | jq '.groups[1].payment_address = "0xc7973537517BfDeA79EE11Fa2D52584241a34dF2"' >service_metadata2.json
#mv -f service_metadata2.json service_metadata.json
#
#snet service update-metadata testo tests -yq && exit 1 || echo "fail as expected"

#add assets with single value

snet service metadata-init ./service_spec1/ ExampleService  --metadata-file=service_asset_metadata.json
#cp service_metadata.json service_asset_metadata.json
snet --print-traceback service metadata-add-assets ./service_spec1/test hero_image --metadata-file=service_asset_metadata.json
snet --print-traceback service metadata-add-assets ./service_spec1/test terms_of_use --metadata-file=service_asset_metadata.json
result=$(cat service_asset_metadata.json | jq '.assets.hero_image')
test $result = '"QmWQhwwnvK4YHvEarEguTDhz8o2kwvyfPhv5favs1VS4xm/test"' && echo "add asset with single value  test case passed " || exit 1

#add assets with multiple values
snet --print-traceback service metadata-add-assets ./service_spec1/test images --metadata-file=service_asset_metadata.json
snet --print-traceback service metadata-add-assets ./service_spec1/test images --metadata-file=service_asset_metadata.json
result=$(cat service_asset_metadata.json | jq '.assets.images[1]')
test $result = '"QmWQhwwnvK4YHvEarEguTDhz8o2kwvyfPhv5favs1VS4xm/test"' && echo "add asset with multiple value  test case passed " || exit 1

#remove assets
snet --print-traceback service metadata-remove-assets hero_image --metadata-file=service_asset_metadata.json
result=$(cat service_asset_metadata.json | jq '.assets.hero_image')
test $result = '""' && echo "metadata-remove-assets  test case passed " || exit 1

#remove all assets
snet --print-traceback service metadata-remove-all-assets --metadata-file=service_asset_metadata.json
result=$(cat service_asset_metadata.json | jq '.assets')
test $result = '{}' && echo "metadata-remove-all-assets test case passed " || exit 1
rm service_asset_metadata.json
