# Test "snet network"

snet network create local_bad http://localhost:8080 && exit 1 || echo "fail as expected"

# create network without check
snet network create local_bad http://localhost:8080 --skip-check

#switch to this network
snet network local_bad

#switch to mainnet
snet network mainnet

#switch to ropsten
snet network ropsten

