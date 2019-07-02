# snet-sdk-python
  
SingularityNET SDK for Python
  
## Getting Started  
  
These instructions are for the development and use of the SingularityNET SDK for Python.

### Core concepts
  
The SingularityNET SDK allows you to make calls to SingularityNET services programmatically from your application.  
To communicate between clients and services, SingularityNET uses [gRPC](https://grpc.io/).  
To handle payment of services, SingularityNET uses [Ethereum state channels](https://dev.singularitynet.io/docs/concepts/multi-party-escrow/).  
The SingularityNET SDK abstracts and manages state channels with service providers on behalf of the user and handles authentication with the SingularityNET services.

### Usage
  
To call a SingularityNET service, the user must be able to deposit funds (AGI tokens) to the [Multi-Party Escrow](https://dev.singularitynet.io/docs/concepts/multi-party-escrow/) Smart Contract.  
To deposit these tokens or do any other transaction on the Ethereum blockchain, the user must possess an Ethereum identity with available Ether.


To interact with SingularityNET services, you must compile the appropriate client libraries for that service.   
To generate the client libraries to use in your application, you need the SingularityNET Command Line Interface, or CLI, which you can download from PyPi, see [https://github.com/singnet/snet-cli#installing-with-pip](https://github.com/singnet/snet-cli/snet_cli#installing-with-pip)
  
Once you have the CLI installed, run the following command:
```bash
snet sdk generate-client-library python <org_id> <service_id>
```
  
Optionally, you can specify an output path; otherwise it's going to be `./client_libraries/python/<registry_address>/<org_id>/<service_id>`.  
You should move or copy these generated files to the root of your project.
  
Once you have installed the snet-sdk in your current environment and it's in your PYTHONPATH, you should import it and create an instance of the base sdk class:

```python
from snet_sdk import SnetSDK
from config import config
snet = SnetSDK(config)
```

The `config` parameter must be a Python dictionary.  
See [config.py.sample](https://github.com/singnet/snet-code-examples/blob/master/python/client/config.py.sample) for a sample configuration file.
  
Now, the instance of the sdk can be used to create service client instances. To create a service client instance, it needs to be supplied with the client libraries that you compiled before.  
Specifically, it needs the `Stub` object of the service you want to use from the compiled `_pb2_grpc.py` file of the client library.  
Continuing from the previous code this is an example using `example-service` from the `snet` organization:

```python
import example_service_pb2_grpc

org_id = "snet"
service_id = "example-service"

service_client = sdk.create_service_client(org_id, service_id, example_service_pb2_grpc.CalculatorStub)
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

### Installing

#### Prerequisites  
  
* [Python 3.6.5](https://www.python.org/downloads/release/python-365/)  
* [Node 8+ w/npm](https://nodejs.org/en/download/)

---

* Clone the git repository  
```bash  
$ git clone git@github.com:singnet/snet-cli.git
$ cd snet-cli/snet_sdk
```  
  
* Install development/test blockchain dependencies  
```bash  
$ ./scripts/blockchain install
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
