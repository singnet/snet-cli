from setuptools import setup, find_namespace_packages
from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install


def install_and_compile_proto():
    import snet.snet_cli
    from snet.snet_cli.utils import compile_proto as compile_proto
    from pathlib import Path
    proto_dir = Path(__file__).absolute().parent.joinpath("snet", "snet_cli", "resources", "proto")
    dest_dir = Path(snet.snet_cli.__file__).absolute().parent.joinpath("resources", "proto")
    print(proto_dir, "->", dest_dir)
    for fn in proto_dir.glob('*.proto'):
        print("Compiling protobuf", fn)
        compile_proto(proto_dir, dest_dir, proto_file=fn)


class develop(_develop):
    """Post-installation for development mode."""

    def run(self):
        _develop.run(self)
        self.execute(install_and_compile_proto, (), msg="Compile protocol buffers")


class install(_install):
    """Post-installation for installation mode."""

    def run(self):
        _install.run(self)
        self.execute(install_and_compile_proto, (), msg="Compile protocol buffers")


version_dict = {}
with open("./snet/snet_cli/version.py") as fp:
    exec(fp.read(), version_dict)
setup(
    name='snet.snet-cli',
    version=version_dict['__version__'],
    packages=find_namespace_packages(include=['snet.*']),
    namespace_packages=['snet'],
    url='https://github.com/singnet/snet-cli',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET CLI standalone namespace package',
    python_requires='>=3.6',
    install_requires=[
        'grpcio-tools==1.19.0',
        'jsonrpcclient==2.5.2',
        'web3==4.8.3',
        'mnemonic==0.18',
        'pycoin>=0.80',
        'rlp==1.0.1',
        'pyyaml>=4.2b1',
        'ipfsapi==0.4.2.post1',
        'rfc3986==1.1.0',
        'pymultihash==0.8.2',
        'base58==1.0.2',
        'argcomplete>=1.9.4',
        'grpcio-health-checking==1.19.0'
    ],
    cmdclass={
        'develop': develop,
        'install': install
    },
    include_package_data=True
)
