import sys
import os
import subprocess
from setuptools import find_namespace_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install

from common_dependencies import common_dependencies
from version import __version__

PACKAGE_NAME = 'snet.cli'


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name=PACKAGE_NAME,
    version=__version__,
    packages=find_namespace_packages(include=['snet.*']),
    namespace_packages=['snet'],
    url='https://github.com/singnet/snet-cli',
    author="SingularityNET Foundation",
    author_email="info@singularitynet.io",
    description="SingularityNET CLI",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license="MIT",
    python_requires='>=3.10',
    install_requires=common_dependencies,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'snet = snet.cli:main',
        ],
    }
)
