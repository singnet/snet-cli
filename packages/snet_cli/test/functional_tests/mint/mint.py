from snet.snet_cli.utils.utils import get_web3, get_contract_object


def mint_token():
    amount = 10000000

    w3 = get_web3("http://localhost:8545")
    address = "0x592E3C0f3B038A0D673F19a18a773F993d4b2610"
    contract = get_contract_object(
        w3, contract_file="SingularityNetToken", address=address
    )

    contract.functions.mint(address, amount).call()


if __name__ == "__main__":
    mint_token()
