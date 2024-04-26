# snet-cli

[![CircleCI](https://circleci.com/gh/singnet/snet-cli.svg?style=svg)](https://circleci.com/gh/singnet/snet-cli)
  
SingularityNET CLI

## Package

The package is published in PyPI at the following link:

|Package                                       |Description                                                          |
|----------------------------------------------|---------------------------------------------------------------------|
|[snet-cli](https://pypi.org/project/snet.cli/)|Command line interface to interact with the SingularityNET platform  |

## License  
  
This project is licensed under the MIT License - see the
[LICENSE](https://github.com/singnet/snet-cli/blob/master/LICENSE) file for details.

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
$ pip3 install snet.cli
```


### Enabling commands autocompletion
If you want to enable the autocompletion of commands, you should install the
* python-argcomplete

On ubuntu (or any Linux distribution with APT support), you could run the following

```bash
sudo apt install python3-argcomplete
```
After the package is installed, activate autocomplete 

##### for all python commands (which includes snet commands as well) 

```bash
sudo activate-global-python-argcomplete3
```
Note: Changes will not take effect until shell is restarted.

##### OR

##### only for snet commands, then you should run the following
```bash
echo 'eval "$(register-python-argcomplete3 snet)"' >> ~/.bashrc
```
then
```bash
source ~/.bashrc
```

## Usage

Complete documentation is available [here](http://snet-cli-docs.singularitynet.io/)

### Example service call via the CLI
We will use the Sepolia testnet for this example:
```bash
snet network sepolia
```
Create the identity:
```bash
snet identity create example_identity key
```
and enter your private key when asked.  
OR  
you can pass the private key directly:
```bash
snet identity create --private-key "a7638fd785fdb5cf13df0a1d7b5584cc20d4e8526403f0df105eedf23728f538" test key
```
You can also use other identity options. See [documentation](http://snet-cli-docs.singularitynet.io/identity.html).  
You can check your balance using the 
```bash
snet account balance
```
Deposit 70 tokens:
```bash
 snet account deposit 70
```
Press y to confirm.  
You can check your balance again to ensure that the transaction was successfull.  
Before making a call we need to open the payment channel. In this example we will use the organization with id= 26072b8b6a0e448180f8c0e702ab6d2f and group_name= default_group. We will transfer there 70 tokens for 4 weeks:
```bash
 snet channel open-init 26072b8b6a0e448180f8c0e702ab6d2f default_group 70 +4weeks
```
And now we can call the "Exampleservice" service:
```bash
 snet client call 26072b8b6a0e448180f8c0e702ab6d2f Exampleservice default_group add '{"a":10,"b":32}'
```
Press 'Y' to confirm and get service`s response:
>value: 42

## Development

### Installation

#### Prerequisites  
  
* [Python 3.10](https://www.python.org/downloads/release/python-31012/)  

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
