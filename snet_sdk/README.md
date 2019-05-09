# snet-sdk-python
  
SingularityNET SDK for Python
  
## Getting Started  
  
These instructions are for the development and use of the SingularityNET SDK for Python.

### Usage

The SingularityNET SDK allows you to import compiled client libraries for your service or services or choice and make calls to those services programmatically from your application by setting up state channels with the providers of those services and making gRPC calls to the SingularityNET daemons for those services by selecting a channel with sufficient funding and supplying the appropriate metadata for authentication.
  
Once you have installed the snet-sdk in your current environment and it's in your PYTHONPATH, you should import it and create an instance of the base sdk class:

```python
from snet_sdk import Snet
import config
snet = Snet(private_key=config.private_key)
```

Now, the instance of the sdk can be used to instantiate clients for SingularityNET services. To interact with those services, the sdk needs to be supplied the compiled client libraries and a reference to their path on your file system.
  
To generate the client libraries, you need the SingularityNET Command Line Interface, or CLI, which you can download from PyPi, see [https://github.com/singnet/snet-cli#installing-with-pip](https://github.com/singnet/snet-cli#installing-with-pip)
  
Once you have the CLI installed, run the following command:
```bash
snet sdk generate-client-library python <org_id> <service_id>
```
  
Optionally, you can specify an output path; otherwise it's going to be `./client_libraries/python/<org_id>/<service_id>`
  
Now, by default the sdk is going to look for those client libraries in the `./grpc/<org_id>/<service_id>` in the directory of the main process of the module it's being imported by.
  
Once you have the generated client libraries in place, you can create an instance of a SingularityNET service client:
```python
client = snet.client("<org_id>", "<service_id>")
```

The client exposes the following properties and methods:
- All of the modules from the generated client library as `client.grpc.<module_name`. These are temporarily added to your PYTHONPATH and imported at runtime
- Functions to open, fund and extend state channels
- Functions to retrieve the list of state channels between you and the service provider from the blockchain
- Functions to get the updated state for a specific channel from the service provider, signed by yourself
- Functions to generate and sign the required metadata to make gRPC calls to the service daemon
  
This is an example of how to make a call to a SingularityNET service in the `snet` organization with the `example-service` service_id using the base SDK and client instances created as shown before:  
```python
stub = client.grpc.example_service_pb2_grpc.CalculatorStub(client.grpc_channel)
request = calculator.grpc.example_service_pb2.Numbers(a=10, b=12)
result = stub.add(request)
print(result)
```
If you have no open state channels with the service provider, you can create one by calling the following function:
```python
client.open_channel()
```
By default, this will create a channel with the shortest possible expiration date and the necessary amount to make 100 service calls.  
Once an open channel is created and funded, the sdk will automatically find and use a funded, non-expired channel.
  
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
$ git clone git@github.com:singnet/snet-sdk-python.git
$ cd snet-sdk-python
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
[tags on this repository](https://github.com/singnet/snet-sdk-python/tags).   
  
## License  
  
This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/snet-sdk-python/blob/master/LICENSE) file for details.
