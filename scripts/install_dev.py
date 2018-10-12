#!/usr/bin/env python3

import os
import pathlib
import shutil
import subprocess
import sys
import argparse

parser = argparse.ArgumentParser(description='Take ABI of platform-contracts from already installed packages')
parser.add_argument('pcdir', help='platform-contract directory')
args = parser.parse_args()

abi_contract_names      = ["Agent", "AgentFactory", "Job", "Registry", "MultiPartyEscrow"]
networks_contract_names = ["AgentFactory", "Registry"]
token_contract_name     = "SingularityNetToken"

pcdir = args.pcdir

assert os.path.isdir(pcdir), 'Directory "" does not exist'%pcdir

npm_location = shutil.which('npm')
if not npm_location:
    raise Exception("This script requires 'npm' to be installed and in your PATH")

if (not os.path.isdir(os.path.join(pcdir, "node_modules"))):
    subprocess.call([npm_location, "install"],     cwd=pcdir)

if (not os.path.isdir(os.path.join(pcdir, "build", "npm-module"))):
    subprocess.call([npm_location, "run-script", "compile"],     cwd=pcdir)
    subprocess.call([npm_location, "run-script", "package-npm"], cwd=pcdir)
    
token_json_src_dir    = os.path.join(pcdir, "node_modules", "singularitynet-token-contracts")
platform_json_src_dir = os.path.join(pcdir, "build",        "npm-module")

contract_json_dest_dir = os.path.join("snet_cli", "resources", "contracts")

os.makedirs(os.path.join(contract_json_dest_dir, "abi"),      exist_ok=True)
os.makedirs(os.path.join(contract_json_dest_dir, "networks"), exist_ok=True)
                

for contract_name in abi_contract_names:
    shutil.copy(os.path.join(platform_json_src_dir, "abi", "%s.json"%contract_name), os.path.join(contract_json_dest_dir, "abi", "%s.json"%contract_name))
for contract_name in networks_contract_names:
    shutil.copy(os.path.join(platform_json_src_dir, "networks", "%s.json"%contract_name), os.path.join(contract_json_dest_dir, "networks", "%s.json"%contract_name))
        
shutil.copy(os.path.join(token_json_src_dir, "abi",      "%s.json"%token_contract_name), os.path.join(contract_json_dest_dir, "abi",      "%s.json"%token_contract_name))
shutil.copy(os.path.join(token_json_src_dir, "networks", "%s.json"%token_contract_name), os.path.join(contract_json_dest_dir, "networks", "%s.json"%token_contract_name))

