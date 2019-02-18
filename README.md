# snet-cli

[![CircleCI](https://circleci.com/gh/singnet/snet-cli.svg?style=svg)](https://circleci.com/gh/singnet/snet-cli)
  
SingularityNET CLI
  
## Getting Started  
  
These instructions are for the development and use of the SingularityNET CLI.

### Installing with pip

#### Install prerequisites

You should have python with version >= 3.6.5 and pip installed.

Additionally you should install the following packages:

* libudev
* libusb 1.0

If you use Ubuntu (or any Linux distribution with APT package support) you should do the following:

```bash
sudo apt-get install libudev-dev libusb-1.0-0-dev
```

#### Install snet-cli using pip

```bash
$ pip3 install snet-cli
```

### Commands

Below is a summary of the available commands and their optional/required parameters:

---

```
snet identity
```

* List available identities

---

```
snet identity create IDENTITY_NAME IDENTITY TYPE [--mnemonic MNEMONIC]
                                                 [--private-key PRIVATE_KEY]
                                                 [--keystore-path KEYSTORE_PATH]
                                                 [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
```

* Create an identity
  * `IDENTITY_NAME`: name of identity to create; must be unique among identities
  * `IDENTITY_TYPE`: type of identity (either `rpc`, `mnemonic`, `key`, `ledger`, or `trezor`)
  * `MNEMONIC`: required only for `mnemonic` identity type;
[bip39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) mnemonic for wallet derivation
  * `PRIVATE_KEY`: required only for `key` identity type; hex-encoded private Ethereum key
  * `KEYSTORE_PATH`: required only for `keystore` identity type; local path of the encrypted JSON file
  * `ETH_RPC_ENDPOINT`: required only for `rpc` identity type; Ethereum JSON-RPC endpoint that manages target account

---

```
snet identity delete IDENTITY_NAME
```

* Delete an identity
  * `IDENTITY_NAME`: name of identity to delete

---

```
snet IDENTITY_NAME
```

* Switch identities
  * `IDENTITY_NAME`: name of identity to assume

---

```
snet network
```

* List available networks

---

```
snet network NETWORK
```

* Switch networks
  * `NETWORK`: name of network to use (either `mainnet`, `kovan`, `ropsten`, or `rinkeby`)

---

```
snet network eth-rpc-endpoint ETH_RPC_ENDPOINT
```

* Switch networks using a target Ethereum JSON-RPC endpoint
  * `ETH_RPC_ENDPOINT`: Ethereum JSON-RPC endpoint (network determined by endpoint)

---

```
snet session
```
* Dump current session state

---

```
snet set KEY VALUE
```
* Set session key
  * `KEY`: target session key:
    * `default_gas_price`: default gas price for transactions
    * `default_eth_rpc_endpoint`: default Ethereum JSON-RPC endpoint
    * `default_wallet_index`: default index of account within a given wallet
    * `identity_name`: name of identity to use for signing
  * `VALUE`: desired value

---

```
snet unset KEY
```

* Unset session key:
  * `KEY`: target session key:
    * `default_gas_price`: default gas price for transactions
    * `default_eth_rpc_endpoint`: default Ethereum JSON-RPC endpoint
    * `default_wallet_index`: default index of account within a given wallet
    * `identity_name`: name of identity to use for signing

---

```
snet client balance
```
* Retrieves balance of the current identity

---

```
snet client deposit [--singularitynettoken SINGULARITYNETTOKEN]
                    [--multipartyescrow MULTIPARTYESCROW]
                    [--gas-price GAS_PRICE]
                    [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                    [--wallet-index WALLET_INDEX] [--yes]
                    [--verbose | --quiet]
                     amount
```
* Deposit AGI tokens to the MPE wallet
 * `AMOUNT`: amount of AGI tokens to deposit in MPE wallet
 * `SINGULARITYNETTOKEN`: address of SingularityNetToken contract, if not specified we read address from "networks"
 * `MULTIPARTYESCROW`: address of MultiPartyEscrow contract, if not specified we read address from "networks"
 * `GAS_PRICE`: override session `default_gas_price`
 * `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
 * `WALLET_INDEX`: override session `default_wallet_index`
 * `--no-confirm`: skip interactive confirmation of transaction payloads
 * `--yes, -y`: accept defaults for any argument that is not provided
 * `--verbose`: print all transaction details
 * `--quiet`: print minimal transaction details
---

```
snet client open_init_channel_registry [-h] [--registry REGISTRY]
           [--group_name GROUP_NAME]
           [--multipartyescrow MULTIPARTYESCROW]
           [--gas-price GAS_PRICE]
           [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
           [--wallet-index WALLET_INDEX]
           [--yes] [--verbose | --quiet]
           organization service amount
           expiration
```
* Open channel with the specified service
 * `organization`:name of organization
 * `service`:     name of service
 * `amount`:      amount of AGI tokens to put in the new channel
 * `expiration`:  expiration time (in blocks) for the new channel (one:block ~ 15 seconds)
 * `REGISTRY`:  address of Registry contract, if not specified we read address from "networks"
 * `GROUP_NAME`:name of payment group for which we want to open the channel. Parameter should be specified only for services with several payment groups
 * `MULTIPARTYESCROW`:address of MultiPartyEscrow contract, if not specified we read address from "networks"
 * `GAS_PRICE`: override session `default_gas_price`
 * `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
 * `WALLET_INDEX`: override session `default_wallet_index`
 * `--no-confirm`: skip interactive confirmation of transaction payloads
 * `--yes, -y`: accept defaults for any argument that is not provided
 * `--verbose`: print all transaction details
 * `--quiet`: print minimal transaction details
---

```
snet client call [-h] [--service SERVICE]
                        [--multipartyescrow MULTIPARTYESCROW]
                        channel_id price endpoint method [params]
```
* Invoke the service
 * `channel_id`: channel_id obtained from the open_init_channel_registry call
 * `price`: price for this call in AGI tokens
 * `endpoint`: service endpoint
 * `method`: target service's method name to call
 * `params`: json-serialized parameters object or path containing json-serialized parameters object (leave emtpy to read from stdin)
 * `SERVICE`: name of protobuf service to call. It should be specified in case of method name conflict.
 * `MULTIPARTYESCROW`:address of MultiPartyEscrow contract, if not specified we read address from "networks"
 ---
 
```
 snet service metadata_init
 
```
* Initializes metadata file
 * `organization`:name of organization
 * `service`:  name of service
 * `amount`:      amount of AGI tokens to put in the new channel
 * `expiration`:  expiration time (in blocks) for the new channel (one:block ~ 15 seconds)
 * `REGISTRY`:   address of Registry contract, if not specified we read address from "networks"
 * `GROUP_NAME`: name of payment group for which we want to open the channel. Parameter should be specified only for services with several payment groups
 ---
 
```
snet service metadata_set_fixed_price [-h]
                                      [--metadata_file METADATA_FILE]
                                      price
```
* Sets the price in AGI tokens for the specified service. 
 * `price`: set price in AGI token for all methods
 * `METADATA_FILE`: service metadata json file (default service_metadata.json)
---
```
snet service metadata_add_endpoints [-h] [--group_name GROUP NAME]
                                    [--metadata_file METADATA FILE]
                                    endpoints [endpoints ...]
```
* Sets the endpoints of the daemon corresponding to the service. The value specified for the endpoint must be used as is in the daemon config file.
 *`endpoints`: endpoints
 * `GROUP NAME`: name of the payment group to which we want to add endpoints. Parameter should be specified in case of several payment groups
 * `METADATA FILE`: service metadata json file (default service_metadata.json)
---
```
snet service publish [-h] [--registry REGISTRY]
                        [--metadata_file METADATA FILE]
                        [--tags [TAGS [TAGS ...]]] [--gas-price GAS_PRICE]
                        [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                        [--wallet-index WALLET_INDEX] [--yes]
                        [--verbose | --quiet]
                        organization service
```
* Publish the service to the network and creates service metadata file on ipfs
 * `organization`: name of organization
 * `service`: name of service
 * `REGISTRY`: address of Registry contract, if not specified we read address from "networks"
 * `METADATA FILE`: service metadata json file (default service_metadata.json)
 * `[TAGS [TAGS ...]]`:tags for service                                                              
 * `GAS_PRICE`: override session `default_gas_price`
 * `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
 * `WALLET_INDEX`: override session `default_wallet_index`
 * `--no-confirm`: skip interactive confirmation of transaction payloads
 * `--yes, -y`: accept defaults for any argument that is not provided
 * `--verbose`: print all transaction details
 * `--quiet`: print minimal transaction details
---

```
snet service delete ORG_NAME SERVICE_NAME
```

* Delete a service by its ORG_NAME and SERVICE_NAME; optionally specify a network
  * `ORG_NAME`: name of the organization
  * `SERVICE_NAME`: name of the service

---

```
snet organization list
```

* List all registered organizations on current network

---

```
snet organization info ORG_NAME
```

* Get information about an organizations
  * `ORG_NAME`: name of the organization
  
---

```
snet organization create [-h] [--gas-price GAS_PRICE]
                              [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                              [--wallet-index WALLET_INDEX] [--no-confirm]
                              [--verbose | --quiet]
                              [--registry-at REGISTRY_ADDRESS]
                              ORG_NAME ORG_MEMBERS
```

* Create an organization
  * `ORG_NAME`: name of the organization
  * `ORG_MEMBERS`: list of members to be added to the organization (comma-separated)

---

```
snet organization delete [-h] [--gas-price GAS_PRICE]
                              [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                              [--wallet-index WALLET_INDEX] [--no-confirm]
                              [--verbose | --quiet]
                              [--registry-at REGISTRY_ADDRESS]
                              ORG_NAME
```

* Delete an organization
  * `ORG_NAME`: name of the organization
  
---

```
snet organization list-services ORG_NAME
```

* List all available services from an organization
  * `ORG_NAME`: name of the organization
  
---

```
snet organization change-owner [-h] [--gas-price GAS_PRICE]
                                    [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                    [--wallet-index WALLET_INDEX]
                                    [--no-confirm] [--verbose | --quiet]
                                    [--registry-at REGISTRY_ADDRESS]
                                    ORG_NAME OWNER_ADDRESS
```

* Change the owner of an organization
  * `ORG_NAME`: name of the organization
  * `OWNER_ADDRESS`: address of the new organization's owner

---

```
snet organization add-members [-h] [--gas-price GAS_PRICE]
                                   [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                   [--wallet-index WALLET_INDEX]
                                   [--no-confirm] [--verbose | --quiet]
                                   [--registry-at REGISTRY_ADDRESS]
                                   ORG_NAME ORG_MEMBERS
```

* Add members to an organization
  * `ORG_NAME`: name of the organization
  * `ORG_MEMBERS`: list of members to be added to the organization (comma-separated)

---

```
snet organization rem-members [-h] [--gas-price GAS_PRICE]
                                   [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                   [--wallet-index WALLET_INDEX]
                                   [--no-confirm] [--verbose | --quiet]
                                   [--registry-at REGISTRY_ADDRESS]
                                   ORG_NAME ORG_MEMBERS
```

* Remove members from an organization
  * `ORG_NAME`: name of the organization
  * `ORG_MEMBERS`: list of members to be removed from the organization (comma-separated)

---

```
snet sdk generate-client-library [-h] [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                      [--registry-at REGISTRY_ADDRESS]
                                      language organization service [protodir] 
```

* Generate compiled client libraries to call services using your language of choice
  * `language`: target client library language
  * `organization`: id of the organization
  * `service`: id of the service
  * `protodir`: directory where to output the generated client libraries

---

## Development

### Installing

#### Prerequisites  
  
* [Python 3.6.5](https://www.python.org/downloads/release/python-365/)  
* [Node 8+ w/npm](https://nodejs.org/en/download/)

---

* Clone the git repository  
```bash  
$ git clone git@github.com:singnet/snet-cli.git
$ cd snet-cli
```  
  
* Install development/test blockchain dependencies  
```bash  
$ ./scripts/blockchain install
```
  
* Install the package in development/editable mode  
```bash  
$ pip3 install -e .
```

### Release  
  
This project is published to [PyPI](https://pypi.org/project/snet-cli/).  
  
### Versioning  
  
We use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags on this repository](https://github.com/singnet/snet-cli/tags).   
  
## License  
  
This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/alpha-daemon/blob/master/LICENSE) file for details.
