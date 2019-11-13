# simple case of one group
snet service metadata-init ./service_spec1/ ExampleService --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --group-name group1

snet organization metadata-init org1 testo
snet organization add-group group1 0x52653A9091b5d5021bed06c5118D24b23620c529 5.5.6.7:8089
snet organization add-group group2 0x52653A9091b5d5021bed06c5118D24b23620c529 1.2.1.1:8089
snet organization create testo -y -q
snet service publish testo tests -y -q

# change group_id

# case with several groups
snet service metadata-init ./service_spec1/ ExampleService --group-name group0 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 9.8.9.8:8080
snet service metadata-add-group group1
snet service metadata-add-endpoints group1 8.8.8.8:22 1.2.3.4:8080

snet service metadata-add-group group2
snet service metadata-add-endpoints group2 8.8.8.8:2 1.2.3.4:800

# this should fail as group0 is not in organization
snet service update-metadata testo tests -yq && exit 1 || echo "fail as expected"
snet service metadata-remove-group group0
snet service update-metadata testo tests -yq


#add assets with single value

snet service metadata-init ./service_spec1/ ExampleService --metadata-file=service_asset_metadata.json
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
