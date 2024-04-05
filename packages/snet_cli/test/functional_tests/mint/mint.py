from snet.contracts import get_contract_object

from packages.snet_cli.snet.snet_cli.utils.utils import get_web3
from web3.gas_strategies.time_based import medium_gas_price_strategy

TRANSACTION_TIMEOUT = 500
DEFAULT_GAS = 300000
HTTP_PROVIDER = "http://localhost:8545"

wallet_address_1 = "0x592E3C0f3B038A0D673F19a18a773F993d4b2610"
contract_address = "0x6e5f20669177f5bdf3703ec5ea9c4d4fe3aabd14"
signer_private_key = (
    "0xc71478a6d0fe44e763649de0a0deb5a080b788eefbbcf9c6f7aef0dd5dbd67e0"
)

initialNonce = 0
mint_amount = 10000000000000000


def _get_nonce(web3, address):
    nonce = web3.eth.get_transaction_count(address)
    if initialNonce >= nonce:
        nonce = initialNonce + 1
    nonce = nonce
    return nonce


def send_transaction(web3, contract_fn, *args):
    txn_hash = _send_signed_transaction(web3, contract_fn, *args)
    return web3.eth.wait_for_transaction_receipt(txn_hash, TRANSACTION_TIMEOUT)


def _send_signed_transaction(web3, wallet_address, contract_fn, *args):
    transaction = contract_fn(*args).buildTransaction(
        {
            "chainId": int(web3.version.network),
            "gas": DEFAULT_GAS,
            "gasPrice": web3.eth.gas_price * 4 / 3,
            "nonce": _get_nonce(web3, wallet_address),
        }
    )

    signed_txn = web3.eth.account.sign_transaction(
        transaction, private_key=signer_private_key
    )
    return web3.to_hex(web3.eth.send_raw_transaction(signed_txn.rawTransaction))


def mint_token():
    w3 = get_web3(HTTP_PROVIDER)
    address_1 = w3.to_checksum_address(wallet_address_1)
    contract = get_contract_object(
        w3, contract_file="SingularityNetToken.json", address=contract_address
    )

    send_transaction(
        w3, wallet_address_1, contract.functions.mint, address_1, int(mint_amount)
    )


if __name__ == "__main__":
    mint_token()
