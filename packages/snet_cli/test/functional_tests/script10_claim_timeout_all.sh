snet service metadata-init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144 --group-name group0 --fixed-price 0.0001 --endpoints 8.8.8.8:2020 9.8.9.8:8080
snet service metadata-add-group group1 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata-add-endpoints 8.8.8.8:22 1.2.3.4:8080 --group-name group1

snet service metadata-add-group group2 0x32267d505B1901236508DcDa64C1D0d5B9DF639a
snet service metadata-add-endpoints 8.8.8.8:2 1.2.3.4:800 --group-name group2

snet organization create testo --org-id testo -y -q
snet service publish testo tests -y -q

EXPIRATION0=$(($(snet channel block-number) - 1))
EXPIRATION1=$(($(snet channel block-number) - 1))
EXPIRATION2=$(($(snet channel block-number) + 100000))

snet account deposit 100 -y -q

assert_balance() {
	MPE_BALANCE=$(snet account balance | grep MPE)
	test ${MPE_BALANCE##*:} = $1
}

# should file because group_name has not been specified
snet channel open-init testo tests 1 $EXPIRATION0 -yq && exit 1 || echo "fail as expected"

snet channel open-init testo tests 0.1 $EXPIRATION0 -yq --group-name group0
snet channel open-init testo tests 1 $EXPIRATION1 -yq --group-name group1
snet channel open-init testo tests 10 $EXPIRATION2 -yq --group-name group2

assert_balance 88.9

# should claim channels 0 and 1, but not 2
snet channel claim-timeout-all -y
assert_balance 90
