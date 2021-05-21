from snet_cli.utils.config import get_contract_address
from packages.snet_cli.snet_cli.commands.commands import BlockchainCommand

blockchain = BlockchainCommand()


def mint_token():
    amount = 1000000000000000000
    address = "0x592E3C0F3B038A0D673F19A18A773F993D4B2610"
    blockchain.transact_contract_command(
        "SingularityNetToken", "mint", [address, amount]
    )


if __name__ == "__main__":
    mint_token()