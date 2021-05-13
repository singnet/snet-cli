import sys
import os
import subprocess
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

PACKAGE_NAME = 'snet'
SOURCES = {
  'snet_cli': 'packages/snet_cli',
  'sdk': 'packages/sdk',
}

def install_packages(sources, develop=False):
    print("installing all packages in {} mode".format(
              "development" if develop else "normal"))
    wd = os.getcwd()
    for k, v in sources.items():
        try:
            os.chdir(os.path.join(wd, v))
            if develop:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-e', '.'])
            else:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '.'])
        except Exception as e:
            print("Oops, something went wrong installing", k)
            print(e)
        finally:
            os.chdir(wd)

class DevelopCmd(develop):
    """ Add custom steps for the develop command """
    def run(self):
        install_packages(SOURCES, develop=True)
        develop.run(self)

class InstallCmd(install):
    """ Add custom steps for the install command """
    def run(self):
        install_packages(SOURCES, develop=False)
        install.run(self)
setup(
    name=PACKAGE_NAME,
    version="0.0.1",
    author="SingularityNET Foundation",
    author_email="info@singularitynet.io",
    description="SingularityNET Monorepo",
    license="MIT",
    cmdclass={
        'install': InstallCmd,
        'develop': DevelopCmd,
    }
)
