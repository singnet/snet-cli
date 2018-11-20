# service side
snet service metadata_init ./service_spec1/ ExampleService 0x42A605c07EdE0E1f648aB054775D6D4E38496144  --encoding json --service_type jsonrpc --group_name group1
snet service metadata_add_group group2 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18
snet service metadata_add_endpoints  8.8.8.8:2020 9.8.9.8:8080 --group_name group1
snet service metadata_add_endpoints  8.8.8.8:22   1.2.3.4:8080 --group_name group2
snet service metadata_set_fixed_price 0.0001
snet service publish_in_ipfs

snet organization create testo -y -q
snet service publish testo tests -y -q
snet service update_add_tags testo tests tag1 tag2 tag3 -y -q
snet service update_remove_tags testo tests tag2 -y -q
snet service print_tags  testo tests
snet service print_metadata  testo tests > /dev/null


# client side
snet client balance --snt 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14
snet client deposit 12345 --snt 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14 -y -q
snet client transfer 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 42 -y -q
snet client withdraw 1 -y -q
snet client open_init_channel_metadata 42 1 --group_name group1 -y  -q
snet client channel_claim_timeout 0 -y -q
snet client channel_extend_add 0 --expiration 10000 --amount 42 -y  -q
snet client open_init_channel_registry  testo tests 1 1000000  --group_name group2 -y -q
snet client print_initialized_channels
snet client print_all_channels
rm -rf ~/.snet/mpe_client/
snet client init_channel_metadata 0
snet client init_channel_registry testo tests 1 
snet client print_initialized_channels
snet client print_all_channels
snet service delete testo tests -y -q
snet organization list-services testo
