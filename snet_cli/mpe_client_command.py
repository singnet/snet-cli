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
        self._printout("signature hex: ")
        self._printout(sign.hex())
        self._printout("signature base64: ")
        self._printout(base64.b64encode(sign))
        
