import os
import sys
import argparse

sys.path.insert(0, os.path.abspath('../../snet_cli'))

from snet_cli import arguments


def create_subcommand_rst(subcommand_contents, name):
    contents = subcommand_contents.replace(
        "<<TITLE_PLACEHOLDER>>", name.title()).replace("<<PATH_PLACEHOLDER>>", name)
    with open(name+".rst", "w") as fp:
        fp.write(contents)
        fp.flush()
        fp.close()


def generate_index_rst(index_contents, subcommand_contents):
    actions_list = arguments.get_parser().__getattribute__('_actions')
    sub_commands = list()
    for action in actions_list:
        if type(action) == argparse._SubParsersAction:
            choices = action.choices
            for key in choices:
                sub_commands.append(str(key).strip())

            sub_commands.sort()
            for key in sub_commands:
                index_contents += "   " + key + "\n"
                if not os.path.exists(key+".rst"):
                    print("File does not exist " + key)
                    create_subcommand_rst(subcommand_contents, key)

    with open("index.rst", "w") as fp:
        fp.write(index_contents)
        fp.flush()
        fp.close()


if not os.path.exists("index_template.tpl"):
    print("index template not found. Unable to proceed")
    exit(1)

if not os.path.exists("subcommand_template.tpl"):
    print("subcommand_template template not found. Unable to proceed")
    exit(1)

with open("index_template.tpl", "r") as fp:
    index_contents = fp.read()
index_contents += "\n"

with open("subcommand_template.tpl", "r") as fp:
    subcommand_contents = fp.read()

generate_index_rst(index_contents, subcommand_contents)
