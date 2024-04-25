import os
from pathlib import Path
from setuptools import find_namespace_packages, setup
from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install

from snet.cli.utils.utils import compile_proto
from version import __version__

PACKAGE_NAME = 'snet.cli'


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


with open("./requirements.txt") as f:
    requirements_str = f.read()
requirements = requirements_str.split("\n")


def install_and_compile_proto():
    proto_dir = Path(__file__).absolute().parent.joinpath(
        "snet", "cli", "resources", "proto")
    print(proto_dir, "->", proto_dir)
    for fn in proto_dir.glob('*.proto'):
        print("Compiling protobuf", fn)
        compile_proto(proto_dir, proto_dir, proto_file=fn)


class develop(_develop):
    """Post-installation for development mode."""

    def run(self):
        _develop.run(self)
        self.execute(install_and_compile_proto, (),
                     msg="Compile protocol buffers")


class install(_install):
    """Post-installation for installation mode."""

    def run(self):
        _install.run(self)
        self.execute(install_and_compile_proto, (),
                     msg="Compile protocol buffers")


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
    install_requires=requirements,
    include_package_data=True,
    cmdclass={
        'develop': develop,
        'install': install,
    },
    entry_points={
        'console_scripts': [
            'snet = snet.cli:main',
        ],
    }
)
