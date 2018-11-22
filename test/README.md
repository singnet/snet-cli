# Tests for snet-cli

We have three layers of tests for snet-cli 
* classical unit tests: [unit_tests](unit_tests)
* functional tests: [functional_tests](functional_tests)
* integration test of the whole system. This test can be found in the
separate repository: [https://github.com/singnet/platform-pipeline]


### Unit tests

You can simply add your unit test in [unit_tests], it will be run
automatically in circleci. In the same directory you can find an
example of unit tests. 

### Functional tests

Our functional tests are *de facto* integration tests with
[platform-contracts](https://github.com/singnet/platform-contracts). 

Functional tests are excecuted in the following environment (see [utils/reset_environment.sh](utils/reset_environment.sh))

* IPFS is running and snet-cli is correctly configured to use it
* local ethereum network (ganache-cli with mnemonics "gauge enact biology destroy normal tunnel
slight slide wide sauce ladder produce") is running, and snet-cli is
configured to use it by default
* There is already one identity in snet-cli. It is "private-key" identity
called "snet-user", which corresponds to the first ganache identity.
* snet-cli already know correct addreses for Registry and MultiPartyEscrow contracts, so you shoundn't set them manualy, however address of SingularityNetToken contract is not set, and you should pass it by hands (address of SingularityNetToken in our environment  0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14)

Examples of tests can be found here: [functional_tests](functional_tests). You should add your tests in
this directory.
