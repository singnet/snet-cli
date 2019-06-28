import pkg_resources
from setuptools import setup, find_namespace_packages


PACKAGE_NAME = 'snet.sdk'


def is_package_installed(package_name):
    installed_modules = [p.project_name for p in pkg_resources.working_set] 
    return package_name in installed_modules


dependencies = []


if is_package_installed('snet-cli'):
    # The default setup.py in the snet_cli package for local development installs the whole snet_cli package, 
    # not the standalone snet.snet_cli namespace package; if a strict dependency on snet.snet_cli was enforced,
    # this setup.py would fetch it from PyPI. So, if snet_cli is installed and in your Python path, the
    # dependency on snet.snet_cli will be skipped.
    # If snet_cli is not available, snet.snet_cli will be fetched from PyPI.
    print("Package 'snet_cli' is installed and in your PYTHONPATH: skipping snet.snet_cli dependency")
else:
    dependencies.append('snet.snet_cli')


version_dict = {}
with open("./snet/sdk/version.py") as fp:
    exec(fp.read(), version_dict)

setup(
    name=PACKAGE_NAME,
    version=version_dict['__version__'],
    packages=find_namespace_packages(include=['snet.*']),
    namespace_packages=['snet'],
    url='https://github.com/singnet/snet-cli/tree/master/snet_sdk',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET Python SDK',
    python_requires='>=3.6',
    install_requires=dependencies
)
