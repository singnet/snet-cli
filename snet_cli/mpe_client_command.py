from snet_cli.commands import BlockchainCommand
from snet_cli.utils import compile_proto
import base64
from pathlib import Path
import json
import sys
import os
import grpc
from eth_account.messages import defunct_hash_message
from web3.utils.encoding import pad_hex
from web3.utils.events import get_event_data
from snet_cli.utils import get_contract_def, abi_get_element_by_name, abi_decode_struct_to_dict
from snet_cli.utils_proto import import_protobuf_from_dir, switch_to_json_payload_econding
from snet_cli.utils import type_converter
from snet_cli.mpe_service_metadata import mpe_service_metadata_from_json, load_mpe_service_metadata
from snet_cli.utils_ipfs import bytesuri_to_hash, get_from_ipfs_and_checkhash
import tarfile
import io
import shutil
import tempfile
from snet_cli.utils_agi2cogs import cogs2stragi


class MPEClientCommand(BlockchainCommand):

    # O. MultiPartyEscrow related functions

    def print_account(self):
        self._printout(self.ident.address)

    # print balance of ETH, AGI, and MPE wallet
    def print_agi_and_mpe_balances(self):
        if (self.args.account):
            account = self.args.account
        else:
            account = self.ident.address
        eth_wei  = self.w3.eth.getBalance(account)
        agi_cogs = self.call_contract_command("SingularityNetToken", "balanceOf", [account])
        mpe_cogs = self.call_contract_command("MultiPartyEscrow",    "balances",  [account])

        # we cannot use _pprint here because it doesn't conserve order yet
        self._printout("    account: %s"%account)
        self._printout("    ETH: %s"%self.w3.fromWei(eth_wei, 'ether'))
        self._printout("    AGI: %s"%cogs2stragi(agi_cogs))
        self._printout("    MPE: %s"%cogs2stragi(mpe_cogs))

    def deposit_to_mpe(self):
        amount      = self.args.amount
        mpe_address = self.get_mpe_address()

        already_approved = self.call_contract_command("SingularityNetToken", "allowance", [self.ident.address, mpe_address])
        if (already_approved < amount):
            self.transact_contract_command("SingularityNetToken", "approve", [mpe_address, amount])
        self.transact_contract_command("MultiPartyEscrow", "deposit", [amount])

    def withdraw_from_mpe(self):
        self.transact_contract_command("MultiPartyEscrow", "withdraw", [self.args.amount])

    def transfer_in_mpe(self):
        self.transact_contract_command("MultiPartyEscrow", "transfer", [self.args.receiver, self.args.amount])

    #TODO: this function is copy paste from mpe_service_command.py
    def _get_service_metadata_from_registry(self):
        params = [type_converter("bytes32")(self.args.organization), type_converter("bytes32")(self.args.service)]
        rez = self.call_contract_command("Registry", "getServiceRegistrationByName", params)
        if (rez[0] == False):
            raise Exception("Cannot find Service %s in Organization %s"%(self.args.service, self.args.organization))
        metadata_hash = bytesuri_to_hash(rez[2])
        metadata_json = get_from_ipfs_and_checkhash(self._get_ipfs_client(), metadata_hash)
        metadata      = mpe_service_metadata_from_json(metadata_json)
        return metadata

    # we make sure that MultiPartyEscrow address from metadata is correct
    def _check_mpe_address_metadata(self, metadata):
        mpe_address = self.get_mpe_address()
        if (str(mpe_address).lower() != str(metadata["mpe_address"]).lower()):
            raise Exception("MultiPartyEscrow contract address from metadata %s do not correspond to current MultiPartyEscrow address %s"%(metadata["mpe_address"], mpe_address))

    def _init_channel_from_metadata(self, channel_dir, metadata):
        self._check_mpe_address_metadata(metadata)
        if (os.path.exists(channel_dir)):
            raise Exception("Directory %s already exists"%channel_dir)
        os.makedirs(channel_dir)
        try:
            spec_dir = os.path.join(channel_dir, "service_spec")
            os.makedirs(spec_dir)
            # take tar of .proto files from ipfs and extract them to channel_dir/service_spec
            spec_tar = get_from_ipfs_and_checkhash(self._get_ipfs_client(), metadata["model_ipfs_hash"])
            with tarfile.open(fileobj=io.BytesIO(spec_tar)) as f:
                f.extractall(spec_dir)

            # compile .proto files
            if (not compile_proto(Path(spec_dir), channel_dir)):
                raise Exception("Fail to compile %s/*.proto"%spec_dir)

            # save service_metadata.json in channel_dir
            metadata.save_pretty(os.path.join(channel_dir, "service_metadata.json"))
        except:
            # it is secure to remove channel_dir, because we've created it
            shutil.rmtree(channel_dir)
            raise

    def _check_channel_is_mine(self, channel_id):
        channel = self._get_channel_state_from_blockchain(channel_id)
        if (channel["sender"].lower() != self.ident.address.lower() and
            channel["signer"].lower() != self.ident.address.lower()):
                raise Exception("Channel %i does not correspond to the current Ethereum identity "%channel_id +
                                "(address=%s sender=%s signer=%s)"%(self.ident.address.lower(), channel["sender"].lower(), channel["signer"].lower()))

    def init_channel_from_metadata(self):
        metadata  = load_mpe_service_metadata(self.args.metadata_file)
        self._check_channel_is_mine(self.args.channel_id)
        self._init_channel_from_metadata(self.get_channel_dir(), metadata)

    def init_channel_from_registry(self):
        channel_dir   = self.get_channel_dir()
        metadata      = self._get_service_metadata_from_registry()
        self._check_channel_is_mine(self.args.channel_id)
        self._init_channel_from_metadata(channel_dir, metadata)

    def _open_channel_for_service(self, metadata):
        group_id    = metadata.get_group_id(self.args.group_name)
        recipient   = metadata.get_payment_address(self.args.group_name)
        rez = self.transact_contract_command("MultiPartyEscrow", "openChannel", [recipient, self.args.amount, self.args.expiration, group_id, self.ident.address])

        if (len(rez[1]) != 1 or rez[1][0]["event"] != "ChannelOpen"):
            raise Exception("We've expected only one ChannelOpen event after openChannel. Make sure that you use correct MultiPartyEscrow address")
        return rez[1][0]["args"]["channelId"]

    def _open_init_channel_from_metadata(self, metadata):
        # try to initilize channel without actually open it (we check metadata and we compile .proto files)
        tmp_dir = tempfile.mkdtemp()
        shutil.rmtree(tmp_dir)
        self._init_channel_from_metadata(tmp_dir, metadata)
        shutil.rmtree(tmp_dir)

        # open payment channel
        channel_id = self._open_channel_for_service(metadata)
        self._printout("#channel_id")
        self._printout(channel_id)

        # move initilize channel to the channel directory
        self._init_channel_from_metadata(self._get_channel_dir(channel_id), metadata)

    def open_init_channel_from_metadata(self):
        metadata  = load_mpe_service_metadata(self.args.metadata_file)
        self._open_init_channel_from_metadata(metadata)

    def open_init_channel_from_registry(self):
        metadata   = self._get_service_metadata_from_registry()
        self._open_init_channel_from_metadata(metadata)

    def channel_claim_timeout(self):
        self.transact_contract_command("MultiPartyEscrow", "channelClaimTimeout", [self.args.channel_id])

    def channel_extend_and_add_funds(self):
        self.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [self.args.channel_id, self.args.expiration, self.args.amount])

    # I. Signature related functions
    def _compose_message_to_sign(self, mpe_address, channel_id, nonce, amount):
        return self.w3.soliditySha3(
               ["address",   "uint256", "uint256", "uint256"],
               [mpe_address, channel_id, nonce,     amount])

    def _sign_message(self, mpe_address, channel_id, nonce, amount):
        message = self._compose_message_to_sign(mpe_address, channel_id, nonce, amount)
        sign    = self.ident.sign_message_after_soliditySha3(message)
        return sign

    def _verify_my_signature(self, signature, mpe_address, channel_id, nonce, amount):
        message      = self._compose_message_to_sign(mpe_address, channel_id, nonce, amount)
        message_hash = defunct_hash_message(message)
        sign_address = self.ident.w3.eth.account.recoverHash(message_hash, signature=signature)
        return sign_address == self.ident.address

    # II. Call related functions (low level)

    # get persistent storage for mpe_client
    def _get_persistent_dir(self):
        return Path.home().joinpath(".snet", "mpe_client")

    # get persistent storage for the given channel (~/.snet/mpe_client/<mpe_address>/<my_address>/<channel-id>/)
    def _get_channel_dir(self, channel_id):
        mpe_address = self.get_mpe_address().lower()
        my_address  = self.ident.address.lower()
        return self._get_persistent_dir().joinpath(mpe_address, my_address, str(channel_id))

    def get_channel_dir(self):
        return self._get_channel_dir(self.args.channel_id)

    def _get_call_params(self):
        params_string = self.args.params

        # try to read from command line
        if params_string is None or params_string == "-":
            self._printerr("Waiting for call params on stdin...")
            params_string = sys.stdin.read()

        # If it is a file, try to read from it
        if Path(params_string).is_file():
            self._printerr("Read call params from the file: %s"%params_string)
            with open(params_string, 'rb') as f:
                params_string = f.read()

        try:
            params = json.loads(params_string)
        except ValueError:
            self._printerr('Decoding JSON has failed (parameters should be in JSON format)')
            raise

        try:
            params = self._transform_call_params(params)
        except Exception as e:
            self._printerr('Fail to "transform" call params')
            raise

        return params

    # possible modifiers: file, b64encode, b64decode
    # format:             modifier1@modifier2@...modifierN@k_final
    def _transform_call_params(self, params):
        rez = {}
        for k, v in params.items():
            # k = modifier1@modifier2@...modifierN@k_final
            k_split = k.split("@")
            k_final = k_split[-1]
            k_mods  = k_split[:-1]
            for m in k_mods:
                if (m == "file"):
                    with open(v, 'rb') as f:
                        v = f.read()
                elif (m == "b64encode"):
                    v = base64.b64encode(v)
                elif (m == "b64decode"):
                    v = base64.b64decode(v)
                else:
                    raise Exception("Unknow modifier ('%s') in call parameters. Possible modifiers: file, b64encode, b64decode"%m)
            rez[k_final] = v
        return rez

    def _import_protobuf_for_channel(self):
        channel_dir = self.get_channel_dir()
        return import_protobuf_from_dir(channel_dir, self.args.method, self.args.service)

    def _call_server_via_grpc_channel(self, grpc_channel, nonce, amount, params, service_metadata):
        stub_class, request_class, response_class = self._import_protobuf_for_channel()

        request  = request_class(**params)
        stub     = stub_class(grpc_channel)
        call_fn  = getattr(stub, self.args.method)

        if service_metadata["encoding"] == "json":
            switch_to_json_payload_econding(call_fn, response_class)

        mpe_address = self.get_mpe_address()
        channel_id  = self.args.channel_id
        signature = self._sign_message(mpe_address, channel_id, nonce, amount)
        metadata = [("snet-payment-type",                 "escrow"                    ),
                    ("snet-payment-channel-id",            str(channel_id)  ),
                    ("snet-payment-channel-nonce",         str(nonce)       ),
                    ("snet-payment-channel-amount",        str(amount)      ),
                    ("snet-payment-channel-signature-bin", bytes(signature))]

        response = call_fn(request, metadata=metadata)
        return response

    def _get_channel_service_metadata(self):
        return load_mpe_service_metadata(self.get_channel_dir().joinpath("service_metadata.json"))

    def call_server_lowlevel(self):
        params           = self._get_call_params()
        grpc_channel     = grpc.insecure_channel(self.args.endpoint)
        service_metadata = self._get_channel_service_metadata()

        response = self._call_server_via_grpc_channel(grpc_channel, self.args.nonce, self.args.amount, params, service_metadata)
        self._printout(response)

    # III. Stateless client related functions
    def _get_channel_state_from_blockchain(self, channel_id):
        abi         = get_contract_def("MultiPartyEscrow")
        channel_abi = abi_get_element_by_name(abi, "channels")
        channel     = self.call_contract_command("MultiPartyEscrow",  "channels", [channel_id])
        channel     = abi_decode_struct_to_dict(channel_abi, channel)
        return channel

    def _print_channels_from_blockchain(self, channels_ids):
        self._printout("#channelId  nonce  recipient  groupId(base64) value(AGI)  expiration(blocks)")
        for i in sorted(channels_ids):
            channel = self._get_channel_state_from_blockchain(i)
            value_agi = cogs2stragi(channel["value"])
            group_id_base64 = base64.b64encode(channel["groupId"]).decode("ascii")
            self._printout("%i %i %s %s %s %i"%(i, channel["nonce"], channel["recipient"], group_id_base64,
                                                   value_agi, channel["expiration"]))


    def print_all_channels_my(self):
        # TODO: check that it is faster to use events to get all channels with the given sender (instead of using channels directly)
        mpe_address = self.get_mpe_address()
        event_signature   = self.ident.w3.sha3(text="ChannelOpen(uint256,address,address,bytes32,address,uint256,uint256)").hex()
        my_address_padded = pad_hex(self.ident.address.lower(), 256)
        logs = self.ident.w3.eth.getLogs({"fromBlock" : self.args.from_block,
                                          "address"   : mpe_address,
                                          "topics"    : [event_signature,  my_address_padded]})
        # If we are sure that ABI will be fixed forever we can do like this:
        # channels_ids = [int(l['data'],16) for l in logs]
        abi           = get_contract_def("MultiPartyEscrow")
        event_abi     = abi_get_element_by_name(abi, "ChannelOpen")
        channels_ids  = [get_event_data(event_abi, l)["args"]["channelId"] for l in logs]

        self._print_channels_from_blockchain(channels_ids)

    def print_initialized_channels_my(self):
        channels_ids = []
        for channel_dir in self._get_channel_dir(0).parent.glob("*"):
            if (channel_dir.name.isdigit()):
                channels_ids.append(int(channel_dir.name))
        self._print_channels_from_blockchain(channels_ids)

    def _get_channel_state_from_server(self, grpc_channel, channel_id):
        # Compile protobuf if needed
        codegen_dir = Path.home().joinpath(".snet", "mpe_client", "state_service")
        proto_dir   = Path(__file__).absolute().parent.joinpath("resources", "proto")
        if (not codegen_dir.joinpath("state_service_pb2.py").is_file()):
            compile_proto(proto_dir, codegen_dir, proto_file = "state_service.proto")

        # make PaymentChannelStateService.GetChannelState call to the daemon
        stub_class, request_class, _ = import_protobuf_from_dir(codegen_dir, "GetChannelState")
        message   = self.w3.soliditySha3(["uint256"], [channel_id])
        signature = self.ident.sign_message_after_soliditySha3(message)

        request   = request_class(channel_id = self.w3.toBytes(channel_id), signature = bytes(signature))

        stub     = stub_class(grpc_channel)
        response = getattr(stub, "GetChannelState")(request)
        # convert bytes to int
        state = dict()
        state["current_nonce"]          = int.from_bytes(response.current_nonce,         byteorder='big')
        state["current_signed_amount"]  = int.from_bytes(response.current_signed_amount, byteorder='big')
        if (state["current_signed_amount"] > 0):
         good = self._verify_my_signature(bytes(response.current_signature), self.get_mpe_address(), channel_id, state["current_nonce"], state["current_signed_amount"])
         if (not good):
             raise Exception("Error in _get_channel_state_from_server. My own signature from the server is not valid.")

        return state

    # we get state of the channel (nonce, amount, unspent_amount)
    # We do it by securely combine information from the server and blockchain
    # https://github.com/singnet/wiki/blob/master/multiPartyEscrowContract/MultiPartyEscrow_stateless_client.md
    def _get_channel_state_statelessly(self, grpc_channel, channel_id):
        server     = self._get_channel_state_from_server    (grpc_channel, channel_id)
        blockchain = self._get_channel_state_from_blockchain(              channel_id)

        if (server["current_nonce"] == blockchain["nonce"]):
            unspent_amount = blockchain["value"] - server["current_signed_amount"]
        else:
            unspent_amount = None # in this case we cannot securely define unspent_amount yet

        return (server["current_nonce"], server["current_signed_amount"], unspent_amount)

    def print_channel_state_statelessly(self):
        grpc_channel = grpc.insecure_channel(self.args.endpoint)
        current_nonce, current_amount, unspent_amount = self._get_channel_state_statelessly(grpc_channel, self.args.channel_id)
        self._printout("current_nonce                  = %i"%current_nonce)
        self._printout("current_signed_amount_in_cogs  = %i"%current_amount)
        self._printout("current_unspent_amount_in_cogs = %s"%str(unspent_amount))

    def _call_check_price(self, service_metadata):
        pricing = service_metadata["pricing"]
        if (pricing["price_model"] == "fixed_price" and pricing["price_in_cogs"] != self.args.price):
            raise Exception("Service price is %s, but you set price %s"%(cogs2stragi(pricing["price_in_cogs"]), cogs2stragi(self.args.price)))

    def call_server_statelessly(self):
        params           = self._get_call_params()
        grpc_channel     = grpc.insecure_channel(self.args.endpoint)
        service_metadata = self._get_channel_service_metadata()

        self._call_check_price(service_metadata)

        current_nonce, current_amount, unspent_amount = self._get_channel_state_statelessly(grpc_channel, self.args.channel_id)
        self._printout("unspent_amount_in_cogs before call (None means that we cannot get it now):%s"%str(unspent_amount))
        response = self._call_server_via_grpc_channel(grpc_channel, current_nonce, current_amount + self.args.price, params, service_metadata)
        self._printout(response)

    #IV. Auxilary functions

    # get the most recent block number
    def print_block_number(self):
         self._printout(self.ident.w3.eth.blockNumber)
