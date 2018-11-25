# This is a part of circleci functional tests
# This script does following:
# - restart ipfs
# - restart ganache and remigrate platform-contracts
# - set correct networks/*json for Registry and MultiPartyEscrow (but not for SingularityNetToken !)
# - reset .snet configuration
# - add snet-user to snet-cli with first ganache idenity


if [ ! $1 = "--i-no-what-i-am-doing" ]; then
   echo "This script is intended to be run from circleci"
   exit 1
fi
      

# I. restart ipfs
killall -q || echo "supress an error"

rm -rf ~/.ipfs/
ipfs init
ipfs bootstrap rm --all
ipfs config Addresses.API /ip4/127.0.0.1/tcp/5002
ipfs config Addresses.Gateway /ip4/0.0.0.0/tcp/8081
nohup ipfs daemon > ipfs.log 2>&1 &


# II. restart ganache and remigrate platform-contracts
killall -q node || echo "supress an error"

cd ../platform-contracts
nohup ./node_modules/.bin/ganache-cli --mnemonic 'gauge enact biology destroy normal tunnel slight slide wide sauce ladder produce' --networkId 829257324 > /dev/null &
./node_modules/.bin/truffle migrate --network local

# III. set correct networks/*json for Registry and MultiPartyEscrow (but not for SingularityNetToken !) 
cd ../snet-cli/

# set contract addresses for our local network
echo '{"829257324":{"events":{},"links":{},"address":"0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e","transactionHash":""}}' > snet_cli/resources/contracts/networks/MultiPartyEscrow.json
echo '{"829257324":{"events":{},"links":{},"address":"0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2","transactionHash":""}}' > snet_cli/resources/contracts/networks/Registry.json
echo '{"829257324":{"events":{},"links":{},"address":"0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14","transactionHash":""}}' > snet_cli/resources/contracts/networks/SingularityNetToken.json

# IV. reset snet-cli configuration
rm -rf ~/.snet

# Configure SNET-CLI for local work
snet || echo "we avoid error message here" > /dev/null  

cat >> ~/.snet/config << EOF
[network.local]
default_eth_rpc_endpoint = http://localhost:8545
EOF

sed -ie '/ipfs/,+2d' ~/.snet/config
cat >> ~/.snet/config << EOF
[ipfs]
default_ipfs_endpoint = http://localhost:5002
EOF

# V. Add first ganache identity to snet 
snet identity create snet-user key --private-key 0xc71478a6d0fe44e763649de0a0deb5a080b788eefbbcf9c6f7aef0dd5dbd67e0
snet identity snet-user

# VI. switch to local network
snet network local
