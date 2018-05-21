# snet-cli
  
SingularityNET CLI
  
## Getting Started  
  
These instructions are intended to facilitate the development and use of the SingularityNET CLI.
  
### Prerequisites  
  
* [Python 3.6.5](https://www.python.org/downloads/release/python-365/)  
* [Node 8+ w/npm](https://nodejs.org/en/download/)  

### Installing (For Use)

* Install using pip
```bash
$ pip install snet-cli
```
  
### Installing (For Development)
  
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
$ pip install -e .
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
                                                 [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
```

* Create an identity
* `IDENTITY_NAME`: name of identity to create; must be unique among identities
* `IDENTITY_TYPE`: type of identity (either `rpc`, `mnemonic`, `key`, `ledger`, or `trezor`)
* `MNEMONIC`: required only for `mnemonic` identity type;
[bip39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) mnemonic for wallet derivation
* `PRIVATE_KEY`: required only for `key` identity type; hex-encoded private Ethereum key
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
snet network NETWORK_NAME
```

* Switch networks
* `NETWORK_NAME`: name of network to use (either `mainnet`, `kovan`, `ropsten`, or `rinkeby`)

---

```
snet network endpoint ENDPOINT
```

* Switch networks using a target Ethereum JSON-RPC endpoint
* `ENDPOINT`: Ethereum JSON-RPC endpoint (network determined by endpoint)

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
  * `current_agent_at`: current Agent contract address
  * `current_agent_factory_at`: current AgentFactory contract address
  * `default_gas_price`: default gas price for transactions
  * `default_eth_rpc_endpoint`: default Ethereum JSON-RPC endpoint
  * `default_wallet_index`: default index of account within a given wallet
  * `current_job_at`: current Job contract address
  * `current_registry_at`: current Registry contract address
  * `identity_name`: name of identity to use for signing
* `VALUE`: desired value

---

```
snet unset KEY
```

* Unset session key:
  * `current_agent_at`: current Agent contract address
  * `current_agent_factory_at`: current AgentFactory contract address
  * `default_gas_price`: default gas price for transactions
  * `default_eth_rpc_endpoint`: default Ethereum JSON-RPC endpoint
  * `default_wallet_index`: default index of account within a given wallet
  * `current_job_at`: current Job contract address
  * `current_registry_at`: current Registry contract address
  * `identity_name`: name of identity to use for signing

---

```
snet agent [--at AT] create-jobs [--number NUMBER]
                                 [--max-price MAX_PRICE]
                                 [--funded]
                                 [--signed]
                                 [--gas-price GAS_PRICE]
                                 [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                 [--wallet-index WALLET_INDEX]
                                 [--no-confirm]
                                 [--verbose | --quiet]
```

* Create jobs associated with an agent and output their information; overwrites session `current_job_at` to the last
created Job contract's address
* `AT`: address of target Agent contract; overwrites session `current_agent_at`
* `NUMBER`: number of jobs to create
* `MAX_PRICE`: skip interactive confirmation of job price if below this value
* `--funded`: fund created jobs
* `--signed`: sign created job addresses
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet agent-factory [--at AT] create-agent PRICE ENDPOINT [--gas-price GAS_PRICE]
                                                         [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                                         [--wallet-index WALLET_INDEX]
                                                         [--no-confirm]
                                                         [--verbose | --quiet]
```

* Create an agent; overwrites session `current_agent_at` to created Agent contract's address
* `AT`: address of target AgentFactory contract; overwrites session `current_agent_factory_at` (not required for
networks on which AgentFactory has been deployed by SingularityNET Foundation)
* `PRICE`: initial job price for created agent
* `ENDPOINT`: endpoint on which daemon for the new agent will listen for requests
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet client call METHOD PARAMS [--max-price MAX_PRICE]
                               [--agent-at AGENT_AT]
                               [--job-at JOB_AT]
                               [--gas-price GAS_PRICE]
                               [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                               [--wallet-index WALLET_INDEX]
                               [--no-confirm]
                               [--verbose | --quiet]
```

* Call a SingularityNET service
* `METHOD`: service's target JSON-RPC method name
* `PARAMS`: serialized JSON object containing target JSON-RPC method's parameters and call arguments
* `MAX_PRICE`: skip interactive confirmation of job price if below this value
* `AGENT_AT`: address of Agent contract associated with service; overwrites session `current_agent_at`
* `JOB_AT`: address of Job contract instance; continue existing job from current state or create a new job if not
provided or in COMPLETED state; overwrites session `current_job_at`
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet registry [--at AT] create-record NAME AGENT_ADDRESS [--gas-price GAS_PRICE]
                                                         [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                                         [--wallet-index WALLET_INDEX]
                                                         [--no-confirm]
                                                         [--verbose | --quiet]
```

* Create a registry record
* `AT`: address of target Registry contract; overwrites session `current_registry_at` (not required for networks on
which Registry has been deployed by SingularityNET Foundation)
* `NAME`: desired name; must be unique within registry
* `AGENT_ADDRESS`: address of agent to which record refers
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet registry [--at AT] update-record NAME AGENT_ADDRESS [--gas-price GAS_PRICE]
                                                         [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                                         [--wallet-index WALLET_INDEX]
                                                         [--no-confirm]
                                                         [--verbose | --quiet]
```

* Update a registry record
* `AT`: address of target Registry contract; overwrites session `current_registry_at` (not required for networks on
which Registry has been deployed by SingularityNET Foundation)
* `NAME`: existing record name
* `AGENT_ADDRESS`: replacement address of agent to which record refers
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet registry [--at AT] deprecate-record NAME [--gas-price GAS_PRICE]
                                              [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                              [--wallet-index WALLET_INDEX]
                                              [--no-confirm]
                                              [--verbose | --quiet]
```

* Deprecate a registry record
* `AT`: address of target Registry contract; overwrites session `current_registry_at` (not required for networks on
which Registry has been deployed by SingularityNET Foundation)
* `NAME`: existing record name
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet registry [--at AT] list-records [--gas-price GAS_PRICE]
                                     [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                     [--wallet-index WALLET_INDEX]
                                     [--no-confirm]
                                     [--verbose | --quiet]
```

* List registry records
* `AT`: address of target Registry contract; overwrites session `current_registry_at` (not required for networks on
which Registry has been deployed by SingularityNET Foundation)
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet registry [--at AT] query NAME [--gas-price GAS_PRICE]
                                   [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                   [--wallet-index WALLET_INDEX]
                                   [--no-confirm]
                                   [--verbose | --quiet]
```

* Query registry records for a given name; overwrites session `current_agent_at` to the Agent contract address
associated with the given name
* `AT`: address of target Registry contract; overwrites session `current_registry_at` (not required for networks on
which Registry has been deployed by SingularityNET Foundation)
* `NAME`: existing record name
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

```
snet contract <ContractName> [--at AT] <functionName> PARAM1, PARAM2, ... [--transact]
                                                                          [--gas-price GAS_PRICE]
                                                                          [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
                                                                          [--wallet-index WALLET_INDEX]
                                                                          [--no-confirm]
                                                                          [--verbose | --quiet]
```

* Interact with a contract
* `<ContractName>`: name of contract (either `Agent`, `AgentFactory`, `Job`, `Registry`, or `SingularityNetToken`)
* `AT`: address of target contract
* `<functionName>`: name of contract's target function
* `PARAM1, PARAM2, ...`: arguments to pass to given function
* `--transact`: conduct interaction as a transaction rather than a call
* `GAS_PRICE`: override session `default_gas_price`
* `ETH_RPC_ENDPOINT`: override session `default_eth_rpc_endpoint`
* `WALLET_INDEX`: override session `default_wallet_index`
* `--no-confirm`: skip interactive confirmation of transaction payloads
* `--verbose`: print all transaction details
* `--quiet`: print minimal transaction details

---

## Release  
  
This project is published to [PyPI](https://pypi.org/project/snet-cli/).  
  
## Versioning  
  
We use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags on this repository](https://github.com/singnet/snet-cli/tags).   
  
## License  
  
This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/alpha-daemon/blob/master/LICENSE) file for details.