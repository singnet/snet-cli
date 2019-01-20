from snet_cli.mpe_service_command import MPEServiceCommand
from snet_cli.utils import compile_proto
import base64
from pathlib import Path
import os
from snet_cli.utils import get_contract_def, abi_get_element_by_name, abi_decode_struct_to_dict
from snet_cli.mpe_service_metadata import load_mpe_service_metadata
from snet_cli.utils_ipfs import safe_extract_proto_from_ipfs
import shutil
import tempfile
from snet_cli.utils_agi2cogs import cogs2stragi
import pickle
from web3.utils.encoding import pad_hex
from web3.utils.events import get_event_data


# we inherit MPEServiceCommand because we need _get_service_metadata_from_registry
class MPEChannelCommand(MPEServiceCommand):

    def _get_persistent_mpe_dir(self):
        """ get persistent storage for mpe """
        return Path.home().joinpath(".snet", "mpe_client")

    def _get_channel_dir(self, channel_id):
        """ get persistent storage for the given channel (~/.snet/mpe_client/<mpe_address>/<channel-id>/) """
        mpe_address = self.get_mpe_address().lower()
        return self._get_persistent_mpe_dir().joinpath(mpe_address, str(channel_id))

    def get_channel_dir(self):
        return self._get_channel_dir(self.args.channel_id)

    def _save_channel_info_dir(self, channel_dir, channel_info):
        fn = os.path.join(channel_dir, "channel_info.pickle")
        pickle.dump( channel_info, open( fn, "wb" ) )

    def _read_channel_info(self, channel_id):
        fn = os.path.join(self._get_channel_dir(channel_id), "channel_info.pickle")
        return pickle.load( open( fn, "rb" ) )

    def _check_mpe_address_metadata(self, metadata):
        """ we make sure that MultiPartyEscrow address from metadata is correct """
        mpe_address = self.get_mpe_address()
        if (str(mpe_address).lower() != str(metadata["mpe_address"]).lower()):
            raise Exception("MultiPartyEscrow contract address from metadata %s do not correspond to current MultiPartyEscrow address %s"%(metadata["mpe_address"], mpe_address))

    def _init_channel_from_metadata(self, channel_dir, metadata, channel_info):
        self._check_mpe_address_metadata(metadata)
        if (os.path.exists(channel_dir)):
            raise Exception("Directory %s already exists"%channel_dir)

        os.makedirs(channel_dir, mode=0o700)
        try:
            spec_dir = os.path.join(channel_dir, "service_spec")
            os.makedirs(spec_dir, mode=0o700)
            safe_extract_proto_from_ipfs(self._get_ipfs_client(), metadata["model_ipfs_hash"], spec_dir)

            # compile .proto files
            if (not compile_proto(Path(spec_dir), channel_dir)):
                raise Exception("Fail to compile %s/*.proto"%spec_dir)

            # save service_metadata.json in channel_dir
            metadata.save_pretty(os.path.join(channel_dir, "service_metadata.json"))

            # save channel_info (we need sender and signer)
            self._save_channel_info_dir(channel_dir, channel_info)
        except:
            # it is secure to remove channel_dir, because we've created it
            shutil.rmtree(channel_dir)
            raise

    def _check_channel_is_mine(self, channel):
        if (channel["sender"].lower() != self.ident.address.lower() and
            channel["signer"].lower() != self.ident.address.lower()):
                raise Exception("Channel does not correspond to the current Ethereum identity " +
                                 "(address=%s sender=%s signer=%s)"%(self.ident.address.lower(), channel["sender"].lower(), channel["signer"].lower()))

    def _try_init_channel_from_metadata(self, metadata):
        channel = self._get_channel_state_from_blockchain(self.args.channel_id)
        channel_id = self.args.channel_id
        if (channel["sender"].lower() != self.ident.address.lower() and
            channel["signer"].lower() != self.ident.address.lower()):
                raise Exception("Channel %i does not correspond to the current Ethereum identity "%channel_id +
                                "(address=%s sender=%s signer=%s)"%(self.ident.address.lower(), channel["sender"].lower(), channel["signer"].lower()))
        group_name = metadata.get_group_by_group_id(channel["groupId"])
        if (not group_name):
            group_id_base64 = base64.b64encode(channel["groupId"]).decode('ascii')
            raise Exception("Channel %i does not correspond to the given metadata.\n"%channel_id +
                             "We canot find the following group_id in metadata: " + group_id_base64)
        self._printout("#group_name")
        self._printout(group_name["group_name"])
        self._init_channel_from_metadata(self.get_channel_dir(), metadata, channel)

    def init_channel_from_metadata(self):
        metadata  = load_mpe_service_metadata(self.args.metadata_file)
        self._try_init_channel_from_metadata(metadata)

    def init_channel_from_registry(self):
        metadata      = self._get_service_metadata_from_registry()
        self._try_init_channel_from_metadata(metadata)

    def _open_channel_for_service(self, metadata):
        group_id    = metadata.get_group_id(self.args.group_name)
        recipient   = metadata.get_payment_address(self.args.group_name)

        if (self.args.signer):
            signer = self.args.signer
        else:
            signer = self.ident.address

        channel_info = {"sender": self.ident.address, "signer": signer, "recipient": recipient, "groupId" : group_id}
        params = [channel_info["signer"], channel_info["recipient"], channel_info["groupId"], self.args.amount, self.args.expiration]
        rez = self.transact_contract_command("MultiPartyEscrow", "openChannel", params)

        if (len(rez[1]) != 1 or rez[1][0]["event"] != "ChannelOpen"):
            raise Exception("We've expected only one ChannelOpen event after openChannel. Make sure that you use correct MultiPartyEscrow address")
        return rez[1][0]["args"]["channelId"], channel_info

    def _open_init_channel_from_metadata(self, metadata):
        """ try to initialize channel without actually open it (we check metadata and we compile .proto files) """
        tmp_dir = tempfile.mkdtemp()
        shutil.rmtree(tmp_dir)
        self._init_channel_from_metadata(tmp_dir, metadata, {})
        shutil.rmtree(tmp_dir)

        # open payment channel
        channel_id, channel_info = self._open_channel_for_service(metadata)
        self._printout("#channel_id")
        self._printout(channel_id)

        # initialize new channel
        self._init_channel_from_metadata(self._get_channel_dir(channel_id), metadata, channel_info)

    def open_init_channel_from_metadata(self):
        metadata  = load_mpe_service_metadata(self.args.metadata_file)
        self._open_init_channel_from_metadata(metadata)

    def open_init_channel_from_registry(self):
        metadata   = self._get_service_metadata_from_registry()
        self._open_init_channel_from_metadata(metadata)

    def channel_claim_timeout(self):
        rez = self._get_channel_state_from_blockchain(self.args.channel_id)
        if (rez["value"] == 0):
            raise Exception("Channel has 0 value. There is nothing to claim")
        self.transact_contract_command("MultiPartyEscrow", "channelClaimTimeout", [self.args.channel_id])

    def channel_extend_and_add_funds(self):
        self.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [self.args.channel_id, self.args.expiration, self.args.amount])

    def _get_all_initilized_channels(self):
        """ return list of tuples (channel_id, channel_info) """
        channels = []
        for channel_dir in self._get_channel_dir(0).parent.glob("*"):
            if (channel_dir.name.isdigit()):
                channel_id    = int(channel_dir.name)
                channel_info  = self._read_channel_info(channel_id)
                channels.append((channel_id, channel_info))
        return channels

    def _get_channel_state_from_blockchain(self, channel_id):
        abi         = get_contract_def("MultiPartyEscrow")
        channel_abi = abi_get_element_by_name(abi, "channels")
        channel     = self.call_contract_command("MultiPartyEscrow",  "channels", [channel_id])
        channel     = abi_decode_struct_to_dict(channel_abi, channel)
        return channel

    def _print_channels_from_blockchain(self, channels_ids):
        channels_ids = sorted(channels_ids)
        if (self.args.only_id):
            self._printout("#channelId")
            [self._printout(str(i)) for i in channels_ids]
            return
        self._printout("#channelId nonce recipient groupId(base64) value(AGI) expiration(blocks)")
        for i in channels_ids:
            channel = self._get_channel_state_from_blockchain(i)
            value_agi = cogs2stragi(channel["value"])
            group_id_base64 = base64.b64encode(channel["groupId"]).decode("ascii")
            self._printout("%i %i %s %s %s %i"%(i, channel["nonce"], channel["recipient"], group_id_base64,
                                                   value_agi, channel["expiration"]))

    def _filter_channels_sender_signer(self, channels):
        good_id = []
        for channel_id, channel_info in channels:
            not_sender = channel_info["sender"] != self.ident.address
            not_signer = channel_info["signer"] != self.ident.address
            if (self.args.filter_sender and not_sender):
                continue
            if (self.args.filter_signer and not_signer):
                continue
            if (self.args.filter_my and not_sender and not_signer):
                continue
            good_id.append(channel_id)
        return good_id

    def print_initialized_channels(self):
        channels = self._get_all_initilized_channels()
        good_ids = self._filter_channels_sender_signer(channels)
        self._print_channels_from_blockchain(good_ids)

    def print_initialized_channels_filter_group(self):
        channels = self._get_all_initilized_channels()
        metadata = self._get_service_metadata_from_registry()
        group_id = metadata.get_group_id(self.args.group_name)

        # filter channels for specific group_id
        channels = [(cid, cinfo) for cid, cinfo in channels if (cinfo["groupId"] == group_id)]
        good_ids = self._filter_channels_sender_signer(channels)
        self._print_channels_from_blockchain(good_ids)

    def _get_all_filtered_channels(self, topics_without_signature):
        """ get all filtered chanels from blockchain logs """
        mpe_address     = self.get_mpe_address()
        event_signature = self.ident.w3.sha3(text="ChannelOpen(uint256,uint256,address,address,address,bytes32,uint256,uint256)").hex()
        topics = [event_signature] + topics_without_signature
        logs = self.ident.w3.eth.getLogs({"fromBlock" : self.args.from_block, "address"   : mpe_address, "topics"    : topics})
        abi           = get_contract_def("MultiPartyEscrow")
        event_abi     = abi_get_element_by_name(abi, "ChannelOpen")
        channels_ids  = [get_event_data(event_abi, l)["args"]["channelId"] for l in logs]
        return channels_ids

    def get_address_from_arg_or_ident(self, arg):
        if (arg):
            return arg
        return self.ident.address

    def print_all_channels_filter_sender(self):
        address = self.get_address_from_arg_or_ident(self.args.sender)
        address_padded = pad_hex(address.lower(), 256)
        channels_ids = self._get_all_filtered_channels([address_padded])
        self._print_channels_from_blockchain(channels_ids)

    def print_all_channels_filter_recipient(self):
        address = self.get_address_from_arg_or_ident(self.args.recipient)
        address_padded = pad_hex(address.lower(), 256)
        channels_ids = self._get_all_filtered_channels([None,address_padded])
        self._print_channels_from_blockchain(channels_ids)

    def print_all_channels_filter_group(self):
        metadata = self._get_service_metadata_from_registry()
        group_id = metadata.get_group_id(self.args.group_name)
        group_id_hex = "0x" + group_id.hex()
        channels_ids = self._get_all_filtered_channels([None, None, group_id_hex])
        self._print_channels_from_blockchain(channels_ids)

    def print_all_channels_filter_group_sender(self):
        address = self.get_address_from_arg_or_ident(self.args.sender)
        address_padded = pad_hex(address.lower(), 256)
        metadata = self._get_service_metadata_from_registry()
        group_id = metadata.get_group_id(self.args.group_name)
        group_id_hex = "0x" + group_id.hex()
        channels_ids = self._get_all_filtered_channels([address_padded, None, group_id_hex])
        self._print_channels_from_blockchain(channels_ids)

    #Auxilary functions
    def print_block_number(self):
         self._printout(self.ident.w3.eth.blockNumber)
