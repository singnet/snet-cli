# This is a part of circleci functional tests
# This script does following:
# - restart ipfs
# - restart ganache and remigrate platform-contracts
# - set correct networks/*json for Registry and MultiPartyEscrow (but not for SingularityNetToken !)
# - reset .snet configuration
# - add snet-user to snet-cli with first ganache idenity

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root from circleci enviroment" 
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
killall -q ganache-cli || echo "supress an error"

cd ../platform-contracts
nohup ganache-cli --mnemonic 'gauge enact biology destroy normal tunnel slight slide wide sauce ladder produce' > /dev/null &
truffle migrate --network local

# III. set correct networks/*json for Registry and MultiPartyEscrow (but not for SingularityNetToken !) 
npm run-script package-npm
cd ../snet-cli/blockchain
rm -rf node_modules
npm install -S ../../platform-contracts/build/npm-module
cd ../
./scripts/blockchain install


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
