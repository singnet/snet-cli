import os
from pathlib import Path
from setuptools import setup
from setuptools.command.develop import develop as _develop
from setuptools.command.install import install as _install
from setuptools.command.build_py import build_py as _build_py
from grpc_tools import protoc
from pkg_resources import resource_filename

def install_and_compile_proto():
    """
    Compiles protobuf files directly.
    """
    proto_dir = Path(__file__).absolute().parent.joinpath(
        "snet", "cli", "resources", "proto")

    # Locate the standard grpc_tools internal protos (google/protobuf/...)
    grpc_protos_include = resource_filename('grpc_tools', '_proto')

    print(f"Proto directory: {proto_dir}")
    print(f"Grpc include directory: {grpc_protos_include}")

    if not proto_dir.exists():
        print(f"Warning: Proto directory not found at {proto_dir}")
        return

    # glob('*.proto') is non-recursive. It will NOT look inside subfolders.
    for fn in proto_dir.glob('*.proto'):
        print(f"Compiling protobuf: {fn}")

        command = [
            'grpc_tools.protoc',
            f'-I{proto_dir}',
            f'-I{grpc_protos_include}',  # <--- CRITICAL FIX: Add standard protos to include path
            f'--python_out={proto_dir}',
            f'--grpc_python_out={proto_dir}',
            str(fn)
        ]

        if protoc.main(command) != 0:
            print(f"Error: Failed to compile {fn}")
            raise RuntimeError(f"Protocol buffer compilation failed for {fn}")

class build_py(_build_py):
    """
    Override build_py to compile protos before building the wheel.
    This is the hook used by 'python -m build'.
    """
    def run(self):
        self.execute(install_and_compile_proto, (), msg="Compile protocol buffers")
        _build_py.run(self)

class develop(_develop):
    """Post-installation for development mode (pip install -e .)."""
    def run(self):
        self.execute(install_and_compile_proto, (), msg="Compile protocol buffers")
        _develop.run(self)

class install(_install):
    """Post-installation for legacy installation mode."""
    def run(self):
        self.execute(install_and_compile_proto, (), msg="Compile protocol buffers")
        _install.run(self)

setup(
    cmdclass={
        'develop': develop,
        'install': install,
        'build_py': build_py,
    },
)