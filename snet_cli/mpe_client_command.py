from snet_cli.commands import BlockchainCommand
import base64


class MPEClientCommand(BlockchainCommand):
    def sign_message(self):
        # here it is ok to accept address without checksum
        mpe_address = self.w3.toChecksumAddress(self.args.mpe_address)
        
        message = self.w3.soliditySha3(
        ["address",   "uint256",            "uint256",       "uint256"],
        [mpe_address, self.args.channel_id, self.args.nonce, self.args.amount])
        
        sign = self.ident.sign_message_after_soliditySha3(message)
        return sign
    
    def print_sign_message(self):
        sign = self.sign_message()
        print("signature hex: ")
        print(sign.hex())
        print("signature base64: ")
        print(base64.b64encode(sign))
        
