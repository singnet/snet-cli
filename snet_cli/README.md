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

Complete documentation is available [here](http://snet-cli-docs.singularitynet.io/)


## Development

### Installing

#### Prerequisites  
  
* [Python 3.6.5](https://www.python.org/downloads/release/python-365/)  
* [Node 8+ w/npm](https://nodejs.org/en/download/)

---

* Clone the git repository  
```bash  
$ git clone git@github.com:singnet/snet-cli.git
$ cd snet-cli/snet_cli
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
[LICENSE](https://github.com/singnet/snet-cli/blob/master/snet_cli/LICENSE) file for details.
