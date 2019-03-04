
snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529  --fixed-price 0.0001 --endpoints 8.8.8.8:2020

snet organization create testo --org-id testo -y -q
snet service publish testo tests -y -q

snet account deposit 100000000 -yq

snet channel open-init testo tests 123.123 1 -yq

snet channel print-initialized | grep 123.223 && exit 1 || echo "fail as expected"

snet channel extend-add-for-service testo tests --amount 0.1 --expiration 314 -yq
snet channel extend-add-for-service testo tests --amount 0.2 -yq
snet channel extend-add-for-service testo tests --expiration 315 -yq
snet channel print-initialized | grep 123.423
snet channel print-initialized | grep 315


rm -rf ~/.snet/mpe_client
snet channel extend-add-for-service testo tests --amount 0.1 --expiration 315 -yq
snet channel extend-add-for-service testo tests --amount 0.1  -yq
snet channel extend-add-for-service testo tests --expiration 31415  -yq
snet channel print-initialized | grep 123.623
snet channel print-initialized | grep 31415


snet channel open-init testo tests 7777.8888 1 -yq --open-new-anyway
snet channel extend-add-for-service testo tests --amount 0.01 --expiration 314 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-service testo tests --amount 0.01 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-service testo tests --expiration 31477 -yq && exit 1 || echo "fail as expected"

snet channel extend-add-for-service testo tests --amount 0.01 --expiration 314 -yq --channel-id 1
snet channel extend-add-for-service testo tests --amount 0.01  --channel-id 1 -yq
snet channel extend-add-for-service testo tests --expiration 31477 -yq --channel-id 1
snet channel print-initialized | grep 7777.9088
snet channel print-initialized | grep 31477

# multiply payment groups case
snet service metadata-init ./service_spec1/ ExampleService 0x52653A9091b5d5021bed06c5118D24b23620c529  --fixed-price 0.0001 --endpoints 8.8.8.8:2020 --group-name group1
snet service metadata-add-group group2 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata-add-endpoints  8.8.8.8:20202 9.10.9.8:8080 --group-name group2

snet service publish testo tests2 -y -q

snet channel open-init testo tests2 2222.33333 1 -yq --group-name group1

snet channel extend-add-for-service testo tests2 --amount 0.001 --expiration 314 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-service testo tests2 --amount 0.001 -yq && exit 1 || echo "fail as expected"
snet channel extend-add-for-service testo tests2 --expiration 4321 -yq && exit 1 || echo "fail as expected"


snet channel extend-add-for-service testo tests2 --amount 0.001 --expiration 4321 --group-name group1 -yq
snet channel extend-add-for-service testo tests2 --amount 0.001  --group-name group1 -yq
snet channel extend-add-for-service testo tests2 --expiration 4321 --group-name group1 -yq

snet channel print-initialized | grep 2222.33533
snet channel print-initialized | grep 4321


snet channel open-init testo tests2 2222.33333 1 -yq --group-name group2
snet channel extend-add-for-service testo tests2 --amount 0.0001 --expiration 314 -yq --group-name group2
snet channel extend-add-for-service testo tests2 --amount 0.0001  --group-name group2 -yq
snet channel extend-add-for-service testo tests2 --expiration 5643 --group-name group2 -yq
snet channel print-initialized | grep 2222.33353
snet channel print-initialized | grep 5643


rm -rf ~/.snet/mpe_client

snet channel extend-add-for-service testo tests2 --amount 0.00001 --expiration 7654 -yq --group-name group2
snet channel extend-add-for-service testo tests2 --amount 0.00001  --group-name group2 -yq
snet channel extend-add-for-service testo tests2 --expiration 7655 --group-name group2 -yq
snet channel print-initialized | grep 2222.33355
snet channel print-initialized | grep 7655
