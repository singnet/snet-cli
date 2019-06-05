from setuptools import setup, find_packages
import re

version_dict = {}
with open("./snet_sdk/version.py") as fp:
    exec(fp.read(), version_dict)

setup(
    name='snet_sdk',
    version=version_dict['__version__'],
    packages=find_packages(),
    url='https://github.com/singnet/snet-cli/tree/master/snet_sdk',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET Python SDK',
    python_requires='>=3.6',
    install_requires=[
        'grpcio-tools==1.17.1',
        'ecdsa==0.13',
        'web3==4.2.1',
        'ipfsapi==0.4.2.post1',
        'rfc3986==1.1.0'
    ],
    include_package_data=True
)
