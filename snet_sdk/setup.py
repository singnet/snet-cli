from setuptools import setup, find_packages
import re

with open('snet_sdk/__init__.py', 'rt', encoding='utf8') as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
    name='snet_sdk',
    version=version,
    packages=find_packages(),
    url='https://github.com/singnet/snet-sdk-python',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET Python SDK',
    install_requires=[
        'grpcio-tools==1.17.1',
        'ecdsa==0.13',
        'web3==4.2.1',
        'ipfsapi==0.4.2.post1',
        'rfc3986==1.1.0'
    ],
    include_package_data=True
)
