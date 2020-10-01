from pathlib import Path

import web3
from snet.snet_cli.utils.proto_utils import import_protobuf_from_dir
from snet.snet_cli.utils.utils import compile_proto, open_grpc_channel, int4bytes_big, RESOURCES_PATH
from snet_cli.commands.mpe_client import MPEClientCommand
from snet_cli.utils.agi2cogs import cogs2stragi


class MPETreasurerCommand(MPEClientCommand):
    """ We inherit MPEChannelCommand because we need _get_channel_state_from_blockchain """

    def _sign_message_list_unclaimed(self, mpe_address, current_block):
        message = self.w3.soliditySha3(
            ["string",           "address",   "uint256"],
            ["__list_unclaimed", mpe_address, current_block])
        return self.ident.sign_message_after_soliditySha3(message)

    def _sign_message_list_in_progress(self, mpe_address, current_block):
        message = self.w3.soliditySha3(
            ["string",             "address",   "uint256"],
            ["__list_in_progress", mpe_address, current_block])
        return self.ident.sign_message_after_soliditySha3(message)

    def _sign_message_start_claim(self, mpe_address, channel_id, channel_nonce):
        message = self.w3.soliditySha3(
            ["string",           "address",   "uint256",  "uint256"],
            ["__start_claim", mpe_address,   channel_id,   channel_nonce])
        return self.ident.sign_message_after_soliditySha3(message)

    def _get_stub_and_request_classes(self, service_name):
        """ import protobuf and return stub and request class """
        # Compile protobuf if needed
        codegen_dir = Path.home().joinpath(".snet", "mpe_client", "control_service")
        proto_dir = RESOURCES_PATH.joinpath("proto")
        if (not codegen_dir.joinpath("control_service_pb2.py").is_file()):
            compile_proto(proto_dir, codegen_dir,
                          proto_file="control_service.proto")

        stub_class, request_class, _ = import_protobuf_from_dir(
            codegen_dir, service_name)
        return stub_class, request_class

    def _decode_PaymentReply(self, p):
        return {"channel_id":  int4bytes_big(p.channel_id), "nonce": int4bytes_big(p.channel_nonce), "amount": int4bytes_big(p.signed_amount), "signature": p.signature}

    def _call_GetListUnclaimed(self, grpc_channel):
        stub_class, request_class = self._get_stub_and_request_classes(
            "GetListUnclaimed")
        stub = stub_class(grpc_channel)

        mpe_address = self.get_mpe_address()
        current_block = self.ident.w3.eth.blockNumber
        signature = self._sign_message_list_unclaimed(
            mpe_address, current_block)
        request = request_class(
            mpe_address=mpe_address, current_block=current_block, signature=bytes(signature))
        response = getattr(stub, "GetListUnclaimed")(request)

        for p in response.payments:
            if (len(p.signature) > 0):
                raise Exception(
                    "Signature was set in GetListUnclaimed. Response is invalid")

        return [self._decode_PaymentReply(p) for p in response.payments]

    def _call_GetListInProgress(self, grpc_channel):
        stub_class, request_class = self._get_stub_and_request_classes(
            "GetListInProgress")
        stub = stub_class(grpc_channel)

        mpe_address = self.get_mpe_address()
        current_block = self.ident.w3.eth.blockNumber
        signature = self._sign_message_list_in_progress(
            mpe_address, current_block)
        request = request_class(
            mpe_address=mpe_address, current_block=current_block, signature=bytes(signature))
        response = getattr(stub, "GetListInProgress")(request)
        return [self._decode_PaymentReply(p) for p in response.payments]

    def _call_StartClaim(self, grpc_channel, channel_id, channel_nonce):
        stub_class, request_class = self._get_stub_and_request_classes(
            "StartClaim")
        stub = stub_class(grpc_channel)
        mpe_address = self.get_mpe_address()
        signature = self._sign_message_start_claim(
            mpe_address, channel_id, channel_nonce)
        request = request_class(mpe_address=mpe_address, channel_id=web3.Web3.toBytes(
            channel_id), signature=bytes(signature))
        response = getattr(stub, "StartClaim")(request)
        return self._decode_PaymentReply(response)

    def print_unclaimed(self):
        grpc_channel = open_grpc_channel(self.args.endpoint)
        payments = self._call_GetListUnclaimed(grpc_channel)
        self._printout("# channel_id  channel_nonce  signed_amount (AGI)")
        total = 0
        for p in payments:
            self._printout("%i   %i   %s" % (
                p["channel_id"], p["nonce"], cogs2stragi(p["amount"])))
            total += p["amount"]
        self._printout("# total_unclaimed_in_AGI = %s" % cogs2stragi(total))

    def _blockchain_claim(self, payments):
        for payment in payments:
            channel_id = payment["channel_id"]
            amount = payment["amount"]
            sig = payment["signature"]
            if (len(sig) != 65):
                raise Exception(
                    "Length of signature is incorrect: %i instead of 65" % (len(sig)))
            v, r, s = int(sig[-1]), sig[:32], sig[32:64]
            v = v % 27 + 27
            params = [channel_id, amount, amount, v, r, s, False]
            self.transact_contract_command(
                "MultiPartyEscrow", "channelClaim", params)

    def _start_claim_channels(self, grpc_channel, channels_ids):
        """ Safely run StartClaim for given channels """
        unclaimed_payments = self._call_GetListUnclaimed(grpc_channel)
        unclaimed_payments_dict = {
            p["channel_id"]: p for p in unclaimed_payments}

        to_claim = []
        for channel_id in channels_ids:
            if (channel_id not in unclaimed_payments_dict or unclaimed_payments_dict[channel_id]["amount"] == 0):
                self._printout(
                    "There is nothing to claim for channel %i, we skip it" % channel_id)
                continue
            blockchain = self._get_channel_state_from_blockchain(channel_id)
            if (unclaimed_payments_dict[channel_id]["nonce"] != blockchain["nonce"]):
                self._printout(
                    "Old payment for channel %i is still in progress. Please run claim for this channel later." % channel_id)
                continue
            to_claim.append((channel_id,  blockchain["nonce"]))

        payments = [self._call_StartClaim(
            grpc_channel, channel_id, nonce) for channel_id, nonce in to_claim]
        return payments

    def _claim_in_progress_and_claim_channels(self, grpc_channel, channels):
        """ Claim all 'pending' payments in progress and after we claim given channels """
        # first we get the list of all 'payments in progress' in case we 'lost' some payments.
        payments = self._call_GetListInProgress(grpc_channel)
        if (len(payments) > 0):
            self._printout(
                "There are %i payments in 'progress' (they haven't been claimed in blockchain). We will claim them." % len(payments))
            self._blockchain_claim(payments)
        payments = self._start_claim_channels(grpc_channel, channels)
        self._blockchain_claim(payments)

    def claim_channels(self):
        grpc_channel = open_grpc_channel(self.args.endpoint)
        self._claim_in_progress_and_claim_channels(
            grpc_channel, self.args.channels)

    def claim_all_channels(self):
        grpc_channel = open_grpc_channel(self.args.endpoint)
        # we take list of all channels
        unclaimed_payments = self._call_GetListUnclaimed(grpc_channel)
        channels = [p["channel_id"] for p in unclaimed_payments]
        self._claim_in_progress_and_claim_channels(grpc_channel, channels)

    def claim_almost_expired_channels(self):
        grpc_channel = open_grpc_channel(self.args.endpoint)
        # we take list of all channels
        unclaimed_payments = self._call_GetListUnclaimed(grpc_channel)

        channels = []
        for p in unclaimed_payments:
            if (p["amount"] == 0):
                continue
            channel_id = p["channel_id"]
            blockchain = self._get_channel_state_from_blockchain(channel_id)
            if (blockchain["expiration"] < self.ident.w3.eth.blockNumber + self.args.expiration_threshold):
                self._printout("We are going to claim channel %i" % channel_id)
                channels.append(channel_id)
        self._claim_in_progress_and_claim_channels(grpc_channel, channels)
