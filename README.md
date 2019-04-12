# snet-cli

[![CircleCI](https://circleci.com/gh/singnet/snet-cli.svg?style=svg)](https://circleci.com/gh/singnet/snet-cli)
  
SingularityNET CLI

## Getting Started  
  
These instructions are for the development and use of the SingularityNET CLI.
For further details, please check our full [Documentation](http://snet-cli-docs.singularitynet.io/).

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


#### Enabling commands autocomplete
If you want to enable auto completion of commands, you should install the following package
* python-argcomplete

On ubuntu (or any Linux distribution with APT package support), you should do the following

```bash
sudo apt install python-argcomplete
```
After the package is installed, activate autocomplete 

##### for all python commands (which includes snet commands as well) 

```bash
sudo activate-global-python-argcomplete
```
Note: Changes will not take effect until shell is restarted.

##### only for snet commands, then you should do the following
```bash
echo 'eval "$(register-python-argcomplete snet)"' >> ~/.bashrc
```
then
```bash
source ~/.bashrc
```

## Commands

Below is a summary of some commands (check the full documentation [here](http://snet-cli-docs.singularitynet.io/)):

---

```
usage: snet [-h] [--print-traceback] COMMAND ...
```

### VERSION

Show version and exit

```
snet version [-h]
```

### IDENTITY

Manage identities

```
snet identity [-h] COMMAND ...
```

#### - list

List of identities

```
snet identity list [-h]
```

#### - create

Create a new identity

```
snet identity create IDENTITY_NAME IDENTITY_TYPE [--mnemonic MNEMONIC]
                                                 [--private-key PRIVATE_KEY]
                                                 [--keystore-path KEYSTORE_PATH]
                                                 [--eth-rpc-endpoint ETH_RPC_ENDPOINT]
```

###### Positional Arguments

* `IDENTITY_NAME`: name of identity to create; must be unique among identities
* `IDENTITY_TYPE`: type of identity (either `rpc`, `mnemonic`, `key`, `ledger`, or `trezor`)
* `MNEMONIC`: required only for `mnemonic` identity type;
[bip39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) mnemonic for wallet derivation
* `PRIVATE_KEY`: required only for `key` identity type; hex-encoded private Ethereum key
* `KEYSTORE_PATH`: required only for `keystore` identity type; local path of the encrypted JSON file
* `ETH_RPC_ENDPOINT`: required only for `rpc` identity type; Ethereum JSON-RPC endpoint that manages target account

#### - delete

Delete an identity

```
snet identity delete [-h] IDENTITY_NAME
```

#### switch to an existing identity

```
snet identity ID_NAME [-h]
```

### NETWORK

Manage networks

```
snet network [-h] NETWORK ...
```

#### - list

List of networks

```
snet network list [-h]
```

#### - create

Create a new network

```
snet network create [-h] [--default-gas-price DEFAULT_GAS_PRICE]
                    [--skip-check]
                    network_name eth_rpc_endpoint
```

###### Positional Arguments

* `network_name`: name of network to create
* `eth_rpc_endpoint`: ethereum rpc endpoint

#### switch to an existing network

```
snet network network_name [-h]
```

### SESSION

View session state

```
snet session [-h]
```

### SET

Set session keys

```
snet set [-h] KEY VALUE
```

###### Positional Arguments

* `KEY`: session key to set from `['default_gas_price', 
                'current_registry_at', 
                'current_multipartyescrow_at', 
                'current_singularitynettoken_at', 
                'default_eth_rpc_endpoint',
                'default_wallet_index', 
                'default_ipfs_endpoint']`
* `VALUE`: desired value of session key

### UNSET

Unset session keys

```
snet unset [-h] KEY
```

###### Positional Arguments

* `KEY`: session key to set from `['default_gas_price', 
                'current_registry_at', 
                'current_multipartyescrow_at', 
                'current_singularitynettoken_at']`

### CONTRACT

Interact with contracts at a low level

```
snet contract [-h] CONTRACT ...
```

### ORGANIZATION

Interact with SingularityNET Organizations

```
snet organization [-h] COMMAND ...
```

#### - list

List of Organizations Ids

```
snet organization list [-h] [--registry-at REGISTRY_ADDRESS]
                       [--wallet-index WALLET_INDEX]
```

#### - list-org-names

List Organizations Names and Ids

```
snet organization list-org-names [-h] [--registry-at REGISTRY_ADDRESS]
                                 [--wallet-index WALLET_INDEX]
```

#### - list-my

Print organization which has the current identity as the owner or as a member

```
snet organization list-my [-h] [--registry-at REGISTRY_ADDRESS]
                          [--wallet-index WALLET_INDEX]
```

#### - info

Organization’s Information

```
snet organization info [-h] [--registry-at REGISTRY_ADDRESS]
                       [--wallet-index WALLET_INDEX]
                       org_id
```

###### Positional Arguments

* `org_id`: name of the organization

#### - create

Create an Organization

```
snet organization create [-h] (--org-id ORG_ID | --auto)
                         [--members ORG_MEMBERS] [--gas-price GAS_PRICE]
                         [--wallet-index WALLET_INDEX] [--yes]
                         [--verbose | --quiet]
                         [--registry-at REGISTRY_ADDRESS]
                         ORG_NAME
```

###### Positional Arguments

* `ORG_NAME`: name of the organization
* `--org-id ORG_ID`: unique organization Id
* `--auto`: generate organization Id (by default random id is generated)
* `--members ORG_MEMBERS[]`: list of members to be added to the organization (comma-separated)

#### - delete

Delete an Organization

```
snet organization delete [-h] [--gas-price GAS_PRICE]
                         [--wallet-index WALLET_INDEX] [--yes]
                         [--verbose | --quiet]
                         [--registry-at REGISTRY_ADDRESS]
                         org_id
```

###### Positional Arguments

* `org_id`: id of the Organization

#### - list-services

List Organization’s services

```
snet organization list-services [-h] [--registry-at REGISTRY_ADDRESS]
                                [--wallet-index WALLET_INDEX]
                                org_id
```

###### Positional Arguments

* `org_id`: id of the Organization

#### - change-name

Change Organization’s name

```
snet organization change-name [-h] [--gas-price GAS_PRICE]
                              [--wallet-index WALLET_INDEX] [--yes]
                              [--verbose | --quiet]
                              [--registry-at REGISTRY_ADDRESS]
                              org_id ORG_NEW_NAME
```

###### Positional Arguments

* `org_id`: id of the Organization
* `ORG_NEW_NAME`: the new Organization's name

#### - change-owner

Change Organization’s owner

```
snet organization change-owner [-h] [--gas-price GAS_PRICE]
                               [--wallet-index WALLET_INDEX] [--yes]
                               [--verbose | --quiet]
                               [--registry-at REGISTRY_ADDRESS]
                               org_id OWNER_ADDRESS
```

###### Positional Arguments

* `org_id`: id of the Organization
* `OWNER_ADDRESS`: address of the new Organization's owner

#### - add-members

Add members to Organization

```
snet organization add-members [-h] [--gas-price GAS_PRICE]
                              [--wallet-index WALLET_INDEX] [--yes]
                              [--verbose | --quiet]
                              [--registry-at REGISTRY_ADDRESS]
                              org_id ORG_MEMBERS
```

###### Positional Arguments

* `org_id`: id of the Organization
* `ORG_MEMBERS[]`: list of members to be added to the organization

#### - rem-members

Remove members from Organization

```
snet organization rem-members [-h] [--gas-price GAS_PRICE]
                              [--wallet-index WALLET_INDEX] [--yes]
                              [--verbose | --quiet]
                              [--registry-at REGISTRY_ADDRESS]
                              org_id ORG_MEMBERS
```

###### Positional Arguments

* `org_id`: id of the Organization
* `ORG_MEMBERS[]`: list of members to be removed from the organization

### ACCOUNT

AGI account

```
snet account [-h] COMMAND ...
```

#### - print

Print the current ETH account

```
snet account print [-h] [--wallet-index WALLET_INDEX]
```

#### - balance

Print balance of AGI tokens and balance of MPE wallet

```
snet account balance [-h] [--account ACCOUNT]
                     [--singularitynettoken-at SINGULARITYNETTOKEN_AT]
                     [--multipartyescrow-at MULTIPARTYESCROW_AT]
                     [--wallet-index WALLET_INDEX]
```

###### Optional Arguments

* `--account ACCOUNT`: account to print balance for (default is the current identity)

#### - deposit

Deposit AGI tokens to MPE wallet

```
snet account deposit [-h] [--singularitynettoken-at SINGULARITYNETTOKEN_AT]
                     [--multipartyescrow-at MULTIPARTYESCROW_AT]
                     [--gas-price GAS_PRICE] [--wallet-index WALLET_INDEX]
                     [--yes] [--verbose | --quiet]
                     amount
```

###### Positional Arguments

* `amount`: amount of AGI tokens to deposit in MPE wallet

#### - withdraw

Withdraw AGI tokens from MPE wallet

```
snet account withdraw [-h] [--multipartyescrow-at MULTIPARTYESCROW_AT]
                      [--gas-price GAS_PRICE] [--wallet-index WALLET_INDEX]
                      [--yes] [--verbose | --quiet]
                      amount
```

###### Positional Arguments

* `amount`: amount of AGI tokens to deposit in MPE wallet

#### - transfer

Transfer AGI tokens inside MPE wallet

```
snet account transfer [-h] [--multipartyescrow-at MULTIPARTYESCROW_AT]
                      [--gas-price GAS_PRICE] [--wallet-index WALLET_INDEX]
                      [--yes] [--verbose | --quiet]
                      receiver amount
```

###### Positional Arguments

* `receiver`: address of the receiver
* `amount`: amount of AGI tokens to deposit in MPE wallet

### CHANNEL

Interact with SingularityNET payment channels

```
snet channel [-h] COMMAND ...
```

#### - init

Initialize channel taking service metadata from Registry

```
snet channel init [-h] [--registry-at REGISTRY_AT]
                  [--multipartyescrow-at MULTIPARTYESCROW_AT]
                  org_id service_id channel_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `channel_id`: channel_id

#### - init-metadata

Initialize channel using service metadata

```
snet channel init-metadata [-h] [--registry-at REGISTRY_AT]
                           [--metadata-file METADATA_FILE]
                           [--multipartyescrow-at MULTIPARTYESCROW_AT]
                           [--wallet-index WALLET_INDEX]
                           org_id service_id channel_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `channel_id`: channel_id

#### - open-init

Open and initialize channel using metadata from Registry

```
snet channel open-init [-h] [--registry-at REGISTRY_AT] [--force]
                       [--signer SIGNER] [--group-name GROUP_NAME]
                       [--multipartyescrow-at MULTIPARTYESCROW_AT]
                       [--gas-price GAS_PRICE] [--wallet-index WALLET_INDEX]
                       [--yes] [--verbose | --quiet] [--open-new-anyway]
                       [--from-block FROM_BLOCK]
                       org_id service_id amount expiration
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `amount`: amount of AGI tokens to put in the new channel
* `expiration`: expiration time in blocks (int), or in blocks
                related to the current_block (+int_blocks), or in
                days related to the current_block and assuming 15
                sec/block (+int_days)

#### - open-init-metadata

Open and initialize channel using service metadata

```
snet channel open-init-metadata [-h] [--registry-at REGISTRY_AT] [--force]
                                [--signer SIGNER] [--group-name GROUP_NAME]
                                [--multipartyescrow-at MULTIPARTYESCROW_AT]
                                [--gas-price GAS_PRICE]
                                [--wallet-index WALLET_INDEX] [--yes]
                                [--verbose | --quiet] [--open-new-anyway]
                                [--from-block FROM_BLOCK]
                                [--metadata-file METADATA_FILE]
                                org_id service_id amount expiration
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `amount`: amount of AGI tokens to put in the new channel
* `expiration`: expiration time in blocks (int), or in blocks
                related to the current_block (+int_blocks), or in
                days related to the current_block and assuming 15
                sec/block (+int_days)

###### Optional Argument

* `--metadata-file METADATA_FILE`: service metadata json file (default `service_metadata.json`)

#### - claim-timeout

Claim timeout of the channel

```
snet channel claim-timeout [-h] [--multipartyescrow-at MULTIPARTYESCROW_AT]
                           [--gas-price GAS_PRICE]
                           [--wallet-index WALLET_INDEX] [--yes]
                           [--verbose | --quiet]
                           channel_id
```

###### Positional Arguments

* `channel_id`: channel_id

#### - claim-timeout-all

Claim timeout for all channels which have current identity as a sender.

```
snet channel claim-timeout-all [-h]
                               [--multipartyescrow-at MULTIPARTYESCROW_AT]
                               [--gas-price GAS_PRICE]
                               [--wallet-index WALLET_INDEX] [--yes]
                               [--verbose | --quiet] [--from-block FROM_BLOCK]
```

#### - extend-add

Set new expiration for the channel and add funds

```
snet channel extend-add [-h] [--expiration EXPIRATION] [--force]
                        [--amount AMOUNT]
                        [--multipartyescrow-at MULTIPARTYESCROW_AT]
                        [--gas-price GAS_PRICE] [--wallet-index WALLET_INDEX]
                        [--yes] [--verbose | --quiet]
                        channel_id
```

###### Positional Arguments

* `channel_id`: channel_id

###### Expiration and amount

* `--expiration EXPIRATION`: expiration time in blocks (int), or in blocks related 
                             to the current_block (+int_blocks), or in days related 
                             to the current_block and assuming 15 sec/block (+int_days)
* `--force`: skip check for very high (>6 month) expiration time
* `--amount AMOUNT`: amount of AGI tokens to add to the channel

#### - extend-add-for-service

Set new expiration and add funds for the channel for the given service

```
snet channel extend-add-for-service [-h] [--registry-at REGISTRY_AT]
                                    [--expiration EXPIRATION] [--force]
                                    [--amount AMOUNT]
                                    [--multipartyescrow-at MULTIPARTYESCROW_AT]
                                    [--gas-price GAS_PRICE]
                                    [--wallet-index WALLET_INDEX] [--yes]
                                    [--verbose | --quiet]
                                    [--group-name GROUP_NAME]
                                    [--channel-id CHANNEL_ID]
                                    [--from-block FROM_BLOCK]
                                    org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

###### Expiration and amount

* `--expiration EXPIRATION`: expiration time in blocks (int), or in blocks related 
                             to the current_block (+int_blocks), or in days related 
                             to the current_block and assuming 15 sec/block (+int_days)
* `--force`: skip check for very high (>6 month) expiration time
* `--amount AMOUNT`: amount of AGI tokens to add to the channel

#### - block-number

Print the last ethereum block number

```
snet channel block-number [-h]
```

#### - print-initialized

Print initialized channels.

```
snet channel print-initialized [-h] [--only-id]
                               [--filter-sender | --filter-signer | --filter-my]
                               [--multipartyescrow-at MULTIPARTYESCROW_AT]
                               [--wallet-index WALLET_INDEX]
                               [--registry-at REGISTRY_AT]
```

###### Optional Arguments

* `--only-id`: print only id of channels
* `--filter-sender`: print only channels in which current identity is sender
* `--filter-signer`: print only channels in which current identity is signer
* `--filter-my`: print only channels in which current identity is sender or signer

#### - print-initialized-filter-service

Print initialized channels for the given service (all payment group).

```
snet channel print-initialized-filter-service [-h] [--registry-at REGISTRY_AT]
                                              [--only-id]
                                              [--filter-sender | --filter-signer | --filter-my]
                                              [--multipartyescrow-at MULTIPARTYESCROW_AT]
                                              [--wallet-index WALLET_INDEX]
                                              org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

###### Optional Arguments

* `--only-id`: print only id of channels
* `--filter-sender`: print only channels in which current identity is sender
* `--filter-signer`: print only channels in which current identity is signer
* `--filter-my`: print only channels in which current identity is sender or signer

#### - print-all-filter-sender

Print all channels for the given sender.

```
snet channel print-all-filter-sender [-h] [--only-id]
                                     [--multipartyescrow-at MULTIPARTYESCROW_AT]
                                     [--from-block FROM_BLOCK]
                                     [--wallet-index WALLET_INDEX]
                                     [--sender SENDER]
```

###### Optional Arguments

* `--only-id`: print only id of channels
* `--sender SENDER`: account to set as sender (by default we use the current identity)

#### - print-all-filter-recipient

Print all channels for the given recipient.

```
snet channel print-all-filter-recipient [-h] [--only-id]
                                        [--multipartyescrow-at MULTIPARTYESCROW_AT]
                                        [--from-block FROM_BLOCK]
                                        [--wallet-index WALLET_INDEX]
                                        [--recipient RECIPIENT]
```

###### Optional Arguments

* `--only-id`: print only id of channels
* `--recipient RECIPIENT`: account to set as recipient (by default we use the current identity)

#### - print-all-filter-group

Print all channels for the given service.

```
snet channel print-all-filter-group [-h] [--registry-at REGISTRY_AT]
                                    [--group-name GROUP_NAME] [--only-id]
                                    [--multipartyescrow-at MULTIPARTYESCROW_AT]
                                    [--from-block FROM_BLOCK]
                                    [--wallet-index WALLET_INDEX]
                                    org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

###### Optional Arguments

* `--group-name GROUP_NAME`: name of the payment group. Parameter should be specified only for 
                             services with several payment groups
* `--only-id`: print only id of channels

#### - print-all-filter-group-sender

Print all channels for the given group and sender.

```
snet channel print-all-filter-group-sender [-h] [--registry-at REGISTRY_AT]
                                           [--group-name GROUP_NAME]
                                           [--only-id]
                                           [--multipartyescrow-at MULTIPARTYESCROW_AT]
                                           [--from-block FROM_BLOCK]
                                           [--wallet-index WALLET_INDEX]
                                           [--sender SENDER]
                                           org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

###### Optional Arguments

* `--group-name GROUP_NAME`: name of the payment group. Parameter should be specified only for 
                             services with several payment groups
* `--only-id`: print only id of channels
* `--sender SENDER`: account to set as sender (by default we use the current identity)

### CLIENT

Interact with SingularityNET services

```
snet client [-h] COMMAND ...
```

#### - call

call server. We ask state of the channel from the server if needed. Channel should be already initialized.

```
snet client call [-h] [--service SERVICE] [--wallet-index WALLET_INDEX]
                 [--multipartyescrow-at MULTIPARTYESCROW_AT]
                 [--save-response FILENAME]
                 [--save-field SAVE_FIELD SAVE_FIELD] [--endpoint ENDPOINT]
                 [--group-name GROUP_NAME] [--channel-id CHANNEL_ID]
                 [--from-block FROM_BLOCK] [--yes] [--skip-update-check]
                 org_id service_id method [params]
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `method`: target service's method name to call
* `params`: json-serialized parameters object or path containing
            json-serialized parameters object (leave emtpy to read
            from stdin)

###### Optional Arguments

* `--service SERVICE`: name of protobuf service to call. It should be specified in case of method name conflict.
* `--save-response FILENAME`: save response in the file
* `--save-field SAVE_FIELD SAVE_FIELD`: save specific field in the file (two arguments 'field' and 'file_name' should be specified)
* `--endpoint ENDPOINT`: service endpoint (by default we read it from metadata)
* `--group-name GROUP_NAME`: name of the payment group. Parameter should be specified only for services with several payment groups
* `--channel-id CHANNEL_ID`: channel_id (only in case of multiply initialized channels for the same payment group)

#### - call-lowlevel

Low level function for calling the server. Service should be already initialized.

```
snet client call-lowlevel [-h] [--service SERVICE]
                          [--wallet-index WALLET_INDEX]
                          [--multipartyescrow-at MULTIPARTYESCROW_AT]
                          [--save-response FILENAME]
                          [--save-field SAVE_FIELD SAVE_FIELD]
                          [--endpoint ENDPOINT] [--group-name GROUP_NAME]
                          org_id service_id channel_id nonce amount_in_cogs
                          method [params]
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `channel_id`: channel_id
* `method`: target service's method name to call
* `params`: json-serialized parameters object or path containing
            json-serialized parameters object (leave emtpy to read
            from stdin)

#### - get-channel-state

Get channel state in stateless manner

```
snet client get-channel-state [-h] [--multipartyescrow-at MULTIPARTYESCROW_AT]
                              [--wallet-index WALLET_INDEX]
                              channel_id endpoint
```

###### Positional Arguments

* `channel_id`: channel_id
* `endpoint`: service endpoint

### SERVICE

Create, publish, register, and update SingularityNET services

```
snet service [-h] COMMAND ...
```

#### - metadata-init

Init metadata file with providing protobuf directory (which we publish in IPFS) and display_name (optionally encoding, service_type and payment_expiration_threshold)

```
snet service metadata-init [-h] [--metadata-file METADATA_FILE]
                           [--multipartyescrow-at MULTIPARTYESCROW_AT]
                           [--group-name GROUP_NAME] [--encoding {proto,json}]
                           [--service-type {grpc,jsonrpc,process}]
                           [--payment-expiration-threshold PAYMENT_EXPIRATION_THRESHOLD]
                           [--endpoints [ENDPOINTS [ENDPOINTS ...]]]
                           [--fixed-price FIXED_PRICE]
                           protodir display_name payment_address
```

###### Positional Arguments

* `protodir`: directory which contains protobuf files
* `display_name`: service display name
* `payment_address`: payment_address for the first payment group

#### - metadata-set-model

Publish protobuf model in ipfs and update existed metadata file

```
snet service metadata-set-model [-h] [--metadata-file METADATA_FILE] protodir
```

###### Positional Arguments

* `protodir`: directory which contains protobuf files

#### - metadata-set-fixed-price

Set pricing model as fixed price for all methods

```
snet service metadata-set-fixed-price [-h] [--metadata-file METADATA_FILE] price
```

###### Positional Arguments

* `price`: set fixed price in AGI token for all methods

#### - metadata-add-group

Add new group of replicas

```
snet service metadata-add-group [-h] [--metadata-file METADATA_FILE]
                                group_name payment_address
```

###### Positional Arguments

* `group_name`: name of the new payment group
* `payment_address`: payment_address for this group

#### - metadata-add-endpoints

Add endpoints to the groups

```
snet service metadata-add-endpoints [-h] [--group-name GROUP_NAME]
                                    [--metadata-file METADATA_FILE]
                                    endpoints [endpoints ...]
```

###### Positional Arguments

* `endpoints`: endpoints

#### - metadata-remove-all-endpoints

Remove all endpoints from metadata

```
snet service metadata-remove-all-endpoints [-h]
                                           [--metadata-file METADATA_FILE]
```

#### - metadata-update-endpoints

Remove all endpoints from the group and add new ones

```
snet service metadata-update-endpoints [-h] [--group-name GROUP_NAME]
                                       [--metadata-file METADATA_FILE]
                                       endpoints [endpoints ...]
```

###### Positional Arguments

* `endpoints`: endpoints

#### - metadata-add-description

Add service description

```
snet service metadata-add-description [-h] [--json JSON] [--url URL]
                                      [--description DESCRIPTION]
                                      [--metadata-file METADATA_FILE]
```

###### Optional Arguments

* `--json JSON`: service description in json
* `--url URL`: URL to provide more details of the service
* `--description DESCRIPTION`: some description of what the service does

#### - publish-in-ipfs

Publish metadata only in IPFS, without publishing in Registry

```
snet service publish-in-ipfs [-h] [--metadata-file METADATA_FILE]
                             [--update-mpe-address]
                             [--multipartyescrow-at MULTIPARTYESCROW_AT]
```

#### - publish

Publish service with given metadata

```
snet service publish [-h] [--metadata-file METADATA_FILE]
                     [--update-mpe-address]
                     [--multipartyescrow-at MULTIPARTYESCROW_AT]
                     [--registry-at REGISTRY_AT] [--tags [TAGS [TAGS ...]]]
                     [--gas-price GAS_PRICE] [--wallet-index WALLET_INDEX]
                     [--yes] [--verbose | --quiet]
                     org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `--tags [TAGS [TAGS ...]]`: tags for service

#### - update-metadata

Publish metadata in IPFS and update existed service

```
snet service update-metadata [-h] [--metadata-file METADATA_FILE]
                             [--update-mpe-address]
                             [--multipartyescrow-at MULTIPARTYESCROW_AT]
                             [--registry-at REGISTRY_AT]
                             [--gas-price GAS_PRICE]
                             [--wallet-index WALLET_INDEX] [--yes]
                             [--verbose | --quiet]
                             org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

#### - update-add-tags

Add tags to existed service registration

```
snet service update-add-tags [-h] [--registry-at REGISTRY_AT]
                             [--gas-price GAS_PRICE]
                             [--wallet-index WALLET_INDEX] [--yes]
                             [--verbose | --quiet]
                             org_id service_id tags [tags ...]
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `tags`: tags which will be add

#### - update-remove-tags

Remove tags from existed service registration

```
snet service update-remove-tags [-h] [--registry-at REGISTRY_AT]
                                [--gas-price GAS_PRICE]
                                [--wallet-index WALLET_INDEX] [--yes]
                                [--verbose | --quiet]
                                org_id service_id tags [tags ...]
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `tags`: tags which will be removed

#### - print-metadata

Print service metadata from registry

```
snet service print-metadata [-h] [--registry-at REGISTRY_AT] org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

#### - print-tags

Print tags for given service from registry

```
snet service print-tags [-h] [--registry-at REGISTRY_AT] org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

#### - get-api-metadata

Extract service api (model) to the given protodir. Get model_ipfs_hash from metadata

```
snet service get-api-metadata [-h] [--metadata-file METADATA_FILE] protodir
```

###### Positional Arguments

* `protodir`: directory to which extract api (model)

#### - get-api-registry

Extract service api (model) to the given protodir. Get metadata from registry

```
snet service get-api-registry [-h] [--registry-at REGISTRY_AT]
                              org_id service_id protodir
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service
* `protodir`: directory to which extract api (model)

#### - delete

Delete service registration from registry

```
snet service delete [-h] [--registry-at REGISTRY_AT] [--gas-price GAS_PRICE]
                    [--wallet-index WALLET_INDEX] [--yes]
                    [--verbose | --quiet]
                    org_id service_id
```

###### Positional Arguments

* `org_id`: id of the Organization
* `service_id`: id of service

### TREASURER

Treasurer logic

```
snet treasurer [-h] COMMAND ...
```

#### - print-unclaimed

Print unclaimed payments

```
snet treasurer print-unclaimed [-h] --endpoint ENDPOINT
                               [--wallet-index WALLET_INDEX]
```

###### Optional Arguments

* `--endpoint ENDPOINT`: daemon endpoint

#### - claim

Claim given channels. We also claim all pending ‘payments in progress’ in case we ‘lost’ some payments.

```
snet treasurer claim [-h] --endpoint ENDPOINT [--gas-price GAS_PRICE]
                     [--wallet-index WALLET_INDEX] [--yes]
                     [--verbose | --quiet]
                     channels [channels ...]
```

###### Positional Arguments

* `channels`: channels to claim

###### Optional Arguments

* `--endpoint ENDPOINT`: daemon endpoint

#### - claim-all

Claim all channels. We also claim all pending ‘payments in progress’ in case we ‘lost’ some payments.

```
snet treasurer claim-all [-h] --endpoint ENDPOINT [--gas-price GAS_PRICE]
                         [--wallet-index WALLET_INDEX] [--yes]
                         [--verbose | --quiet]
```

###### Optional Arguments

* `--endpoint ENDPOINT`: daemon endpoint

#### - claim-expired

Claim all channels which are close to expiration date. We also claim all pending ‘payments in progress’ in case we ‘lost’ some payments.

```
snet treasurer claim-expired [-h]
                             [--expiration-threshold EXPIRATION_THRESHOLD]
                             --endpoint ENDPOINT [--gas-price GAS_PRICE]
                             [--wallet-index WALLET_INDEX] [--yes]
                             [--verbose | --quiet]
```

###### Optional Arguments

* `--endpoint ENDPOINT`: daemon endpoint

### SDK

Generate client libraries to call SingularityNET services using your language of choice

```
snet sdk [-h] COMMAND ...
```

#### - generate-client-library

Generate compiled client libraries to call services using your language of choice

```
snet sdk generate-client-library [-h] [--registry-at REGISTRY_AT]
                                 [--wallet-index WALLET_INDEX]
                                 LANGUAGE org_id service_id [PROTODIR]
```

###### Positional Arguments

* `LANGUAGE`: choose target language for the generated client library from ['python']
* `org_id`: id of the Organization
* `service_id`: id of service
* `PROTODIR`: directory where to output the generated client libraries

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

#### Building Docs

* Install sphinx, sphinx-argparse and the rtd theme
```bash
$ pip install sphinx
$ pip install sphinx-argparse
$ pip install sphinx-rtd-theme
``` 

* Run the build-docs.sh in the docs directory
```bash
$ cd docs
$ sh build-docs.sh
```

The documentation is generated under the docs/build/html folder

### Release  
  
This project is published to [PyPI](https://pypi.org/project/snet-cli/).  
  
### Versioning  
  
We use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags on this repository](https://github.com/singnet/snet-cli/tags).   
  
## License  
  
This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/alpha-daemon/blob/master/LICENSE) file for details.
