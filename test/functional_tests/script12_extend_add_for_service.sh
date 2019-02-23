
snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529  --fixed-price 0.0001 --endpoints 8.8.8.8:2020

snet organization create testo --org-id testo -y -q
snet service publish testo tests -y -q

snet account deposit 100000000 -yq
# should file because group_name has not been specified
snet channel open-init testo tests 123.123 1 -yq 

snet channel print-initialized | grep 123.223 && exit 1 || echo "fail as expected"

snet channel extend-add-for-service testo tests --amount 0.1 --expiration 314 -yq
snet channel print-initialized | grep 123.223

