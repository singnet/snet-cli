from setuptools import setup, find_packages, find_namespace_packages

from common_dependencies import common_dependencies, develop, install


version_dict = {}
with open("./snet/snet_cli/version.py") as fp:
    exec(fp.read(), version_dict)

setup(
    name='snet-cli',
    version=version_dict['__version__'],
    packages=find_namespace_packages(include=['snet.*'])+find_packages(),
    namespace_packages=['snet'],
    url='https://github.com/singnet/snet-cli',
    license='MIT',
    author='SingularityNET Foundation',
    author_email='info@singularitynet.io',
    description='SingularityNET CLI',
    python_requires='>=3.6',
    install_requires=common_dependencies + [
        'trezor==0.9.1',
        'ledgerblue==0.1.27',
    ],
    cmdclass={
        'develop': develop,
        'install': install,
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'snet = snet_cli:main',
        ],
    }
)
