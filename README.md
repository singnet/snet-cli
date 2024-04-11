# snet-python-monorepo

[![CircleCI](https://circleci.com/gh/singnet/snet-cli.svg?style=svg)](https://circleci.com/gh/singnet/snet-cli)
  
SingularityNET Python Monorepo

## Packages  
This repository is a monorepo that includes several packages that we publish to PyPI from a shared codebase, specifically:
  
|Package                                       |Description                                                          |
|----------------------------------------------|---------------------------------------------------------------------|
|[snet-cli](https://pypi.org/project/snet-cli/)|Command line interface to interact with the SingularityNET platform  |
|[snet-sdk](https://pypi.org/project/snet.sdk/)|Integrate SingularityNET services seamlessly into Python applications|

## License  
  
This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/snet-cli/blob/master/LICENSE) file for details.


# snet-cli

[![CircleCI](https://circleci.com/gh/singnet/snet-cli.svg?style=svg)](https://circleci.com/gh/singnet/snet-cli)
  
SingularityNET CLI

## Getting Started  
  
The instruction down below describes the installation of the SingularityNET CLI.
Please check our full [Documentation](http://snet-cli-docs.singularitynet.io/).

### Prerequisites

You should have Python>=3.10 with pip installed.

Additionally, you should make sure that you have the following packages in your system:

* libudev
* libusb 1.0

If you use Ubuntu (or any Linux distribution with APT support) you could run the following:

```bash
sudo apt-get install libudev-dev libusb-1.0-0-dev
```

### Install snet-cli using pip

```bash
$ pip3 install snet.snet-cli
```


### Enabling commands autocompletion
If you want to enable the autocompletion of commands, you should install the
* python-argcomplete

On ubuntu (or any Linux distribution with APT support), you could run the following

```bash
sudo apt install python-argcomplete
```
After the package is installed, activate autocomplete 

##### for all python commands (which includes snet commands as well) 

```bash
sudo activate-global-python-argcomplete
```
Note: Changes will not take effect until shell is restarted.

##### OR

##### only for snet commands, then you should run the following
```bash
echo 'eval "$(register-python-argcomplete snet)"' >> ~/.bashrc
```
then
```bash
source ~/.bashrc
```

## Usage

Complete documentation is available [here](http://snet-cli-docs.singularitynet.io/)


## Development

### Installation

#### Prerequisites  
  
* [Python 3.10.14](https://www.python.org/downloads/release/python-31014/)  

Backward compatibility for other Python versions is not guaranteed.

---

* Clone the git repository  
```bash  
$ git clone https://github.com/singnet/snet-cli.git
$ cd snet-cli/packages/snet_cli
```
  
* Install the package in development/editable mode  
```bash  
$ pip3 install -e .
```

#### Building the Documentation

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
[LICENSE](https://github.com/singnet/snet-cli/blob/master/snet_cli/LICENSE) file for details.

# snet-sdk-python
  
SingularityNET SDK for Python
  
## Getting Started  
  
The instruction below describes the installation of the SingularityNET SDK for Python.

### Core concepts
  
The SingularityNET SDK allows you to make calls to SingularityNET services programmatically from your application.  
To communicate between clients and services, SingularityNET uses [gRPC](https://grpc.io/).  
To handle payment of services, SingularityNET uses [Ethereum state channels](https://dev.singularitynet.io/docs/concepts/multi-party-escrow/).  
The SingularityNET SDK abstracts and manages state channels with service providers on behalf of the user and handles authentication with the SingularityNET services.

### Usage
  
To call a SingularityNET service, the user must be able to deposit funds (AGIX tokens) to the [Multi-Party Escrow](https://dev.singularitynet.io/docs/concepts/multi-party-escrow/) Smart Contract.  
To deposit these tokens or do any other transaction on the Ethereum blockchain, the user must possess an Ethereum identity with available Ether.


To interact with the SingularityNET services, you must compile the appropriate client libraries for that service.   
To generate the client libraries to use in your application, you`ll need the SingularityNET Command Line Interface, or CLI, which you can download from PyPi, see [here](#install-snet-cli-using-pip)
  
Once you have the CLI installed, run the following command:
```bash
snet sdk generate-client-library python <org_id> <service_id>
```
  
Optionally, you can specify an output path; otherwise it's going to be `./client_libraries/python/<registry_address>/<org_id>/<service_id>`.  
You should move or copy these generated files to the root of your project.
  
Once you have installed the snet-sdk in your current environment and it's in your PYTHONPATH, you should import it and create an instance of the base sdk class:

```python
from snet import sdk
from config import config
snet_sdk = sdk.SnetSDK(config)
```

The `config` parameter must be a Python dictionary.  
See [test_sdk_client.py.sample](https://github.com/singnet/snet-cli/blob/master/packages/sdk/testcases/functional_tests/test_sdk_client.py) for a sample configuration file.
 
 ##### Free call configuration
 If you want to use free call you need to add the below-mentioned attributes to the config file.
```         
"free_call_auth_token-bin":"f2548d27ffd319b9c05918eeac15ebab934e5cfcd68e1ec3db2b92765",
"free-call-token-expiry-block":172800,
"email":"test@test.com"  
```
 You can download this config for a given service from [Dapp]([https://beta.singularitynet.io/)
 
Now, the instance of the sdk can be used to create service client instances. To create a service client instance, it needs to be supplied with the client libraries that you have compiled before.  
Specifically, it needs the `Stub` object of the service you want to use from the compiled `_pb2_grpc.py` file of the client library.  
Here is an example using `example-service` from the `snet` organization:

```python
import example_service_pb2_grpc

org_id = "snet"
service_id = "example-service"
group_name="default_group"

service_client = snet_sdk.create_service_client(org_id, service_id,example_service_pb2_grpc.CalculatorStub,group_name)
```

The generated `service_client` instance can be used to call the methods exposed by the service.  
To call these methods, a request object must be provided. Specifically, you should pick the appropriate request message type that is referenced in the stub object.  
Continuing from the previous code this is an example using `example-service` from the `snet` organization:

```python
import example_service_pb2

request = example_service_pb2.Numbers(a=20, b=3)

result = service_client.service.mul(request)
print("Performing 20 * 3: {}".format(result))   # Performing 20 * 3: value: 60.0
```
  
You can get this code example at [https://github.com/singnet/snet-code-examples/tree/python_client/python/client](https://github.com/singnet/snet-code-examples/tree/python_client/python/client)
  
For more information about gRPC and how to use it with Python, please see:
- [gRPC Basics - Python](https://grpc.io/docs/tutorials/basic/python.html)
- [gRPC Python’s documentation](https://grpc.io/grpc/python/)

---

## Development

### Installation

#### Prerequisites  
  
* [Python 3.10.14](https://www.python.org/downloads/release/python-31014/)  

Backward compatibility for other Python versions is not guaranteed.

---

* Clone the git repository  
```bash  
$ git clone git@github.com:singnet/snet-cli.git
$ cd snet-cli/packages/sdk
```
  
* Install the package in development/editable mode  
```bash  
$ pip install -e .
```

### Versioning  
  
We use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags on this repository](https://github.com/singnet/snet-cli/tags).   
  
## License  
  
This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/snet-cli/blob/master/snet_sdk/LICENSE) file for details.
