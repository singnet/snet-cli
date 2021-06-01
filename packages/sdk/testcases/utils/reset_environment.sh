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

cwd=$(pwd)

# I. restart ipfs
ipfs shutdown || echo "supress an error"

rm -rf ~/.ipfs
ipfs init
ipfs bootstrap rm --all
ipfs config Addresses.API /ip4/127.0.0.1/tcp/5002
ipfs config Addresses.Gateway /ip4/0.0.0.0/tcp/8081
nohup ipfs daemon >ipfs.log 2>&1 &

# II. restart ganache and remigrate platform-contracts
killall node || echo "supress an error"

cd ../platform-contracts
nohup ./node_modules/.bin/ganache-cli --mnemonic 'gauge enact biology destroy normal tunnel slight slide wide sauce ladder produce' --networkId 829257324 >/dev/null &
./node_modules/.bin/truffle migrate --network local

# III. remove old snet-cli configuration
rm -rf ~/.snet

# IV. Configure SNET-CLI.

# set correct ipfs endpoint
# (the new new configuration file with default values will be created automatically)
snet set default_ipfs_endpoint http://localhost:5002

# Add local network and switch to it
snet network create local http://localhost:8545

# swith to local network
snet network local

# Configure contract addresses for local network (it will not be necessary for ropsten or mainnet! )
snet set current_singularitynettoken_at 0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14
snet set current_registry_at 0x4e74fefa82e83e0964f0d9f53c68e03f7298a8b2
snet set current_multipartyescrow_at 0x5c7a4290f6f8ff64c69eeffdfafc8644a4ec3a4e

# Create First identity (snet-user = first ganache).
# (snet will automatically swith to this new identity)
snet identity create snet-user rpc --network local
export PYTHONPATH=$cwd
python $cwd"/packages/snet_cli/test/functional_tests/mint/mint.py"
snet account deposit 10000000 -y -q
snet account balance

# service provider has --wallet-index==9 (0x52653A9091b5d5021bed06c5118D24b23620c529)
# make two endpoints (both are actually valid)
cd ../snet-cli/packages/sdk/testcases/


snet organization metadata-init test_org test_org organization
snet organization add-group default_group 0x52653A9091b5d5021bed06c5118D24b23620c529 http://localhost:2379
snet organization create test_org -y -q




snet service metadata-init ./functional_tests/service_spec1/ ExampleService --group-name default_group --fixed-price 0.00001 --endpoints http://localhost:5051
snet service metadata-set-free-calls default_group 2
snet service metadata-set-freecall-signer-address default_group 0x7DF35C98f41F3Af0df1dc4c7F7D4C19a71Dd059F
snet service publish test_org test_service -y -q

snet organization print-metadata test_org test_org
snet service print-metadata test_org test_service


cd ~/singnet/example-service
pip3 install -r requirements.txt
sh buildproto.sh
nohup python3 run_example_service.py --no-daemon &


cd ~/singnet/snet-daemon/snet-daemon-v5.0.1-linux-amd64
nohup ./snetd &

#wait for daemon to come up
sleep 20

cd ~/singnet/snet-cli
 


