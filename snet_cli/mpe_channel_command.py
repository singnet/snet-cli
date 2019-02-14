
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
from collections import defaultdict

# we inherit MPEServiceCommand because we need _get_service_metadata_from_registry
class MPEChannelCommand(MPEServiceCommand):

    def _get_persistent_mpe_dir(self):
        """ get persistent storage for mpe """
        mpe_address      = self.get_mpe_address().lower()
        registry_address = self.get_registry_address().lower()
        return Path.home().joinpath(".snet", "mpe_client", "%s_%s"%(mpe_address, registry_address))

    def _get_service_base_dir(self, org_id, service_id):
        """ get persistent storage for the given service (~/.snet/mpe_client/<mpe_address>_<registry_address>/<org_id>/<service_id>/) """
        return self._get_persistent_mpe_dir().joinpath(org_id, service_id)

    def get_service_spec_dir(self, org_id, service_id):
        """ get persistent storage for the given service (~/.snet/mpe_client/<mpe_address>/<org_id>/<service_id>/service/) """
        return self._get_service_base_dir(org_id, service_id).joinpath("service")

    def get_channel_dir(self, org_id, service_id, channel_id):
        return self._get_service_base_dir(org_id, service_id).joinpath("channels", str(channel_id))

    def _save_channel_info(self, channel_dir, channel_info):
        fn = os.path.join(channel_dir, "channel_info.pickle")
        pickle.dump( channel_info, open( fn, "wb" ) )

    def _read_channel_info(self, org_id, service_id, channel_id):
        fn = os.path.join(self.get_channel_dir(org_id, service_id, channel_id), "channel_info.pickle")
        channel_info = pickle.load( open( fn, "rb" ) )
        channel_info["channelId"] = channel_id
        return channel_info

    def _check_mpe_address_metadata(self, metadata):
        """ we make sure that MultiPartyEscrow address from metadata is correct """
        mpe_address = self.get_mpe_address()
        if (str(mpe_address).lower() != str(metadata["mpe_address"]).lower()):
            raise Exception("MultiPartyEscrow contract address from metadata %s do not correspond to current MultiPartyEscrow address %s"%(metadata["mpe_address"], mpe_address))

    def _init_new_service_from_metadata(self, service_dir, metadata):
        self._check_mpe_address_metadata(metadata)
        if (os.path.exists(service_dir)):
            raise Exception("Directory %s already exists"%service_dir)

        os.makedirs(service_dir, mode=0o700)
        try:
            spec_dir = os.path.join(service_dir, "service_spec")
            os.makedirs(spec_dir, mode=0o700)
            safe_extract_proto_from_ipfs(self._get_ipfs_client(), metadata["model_ipfs_hash"], spec_dir)

            # compile .proto files
            if (not compile_proto(Path(spec_dir), service_dir)):
                raise Exception("Fail to compile %s/*.proto"%spec_dir)

            # save service_metadata.json in channel_dir
            metadata.save_pretty(os.path.join(service_dir, "service_metadata.json"))
        except:
            # it is secure to remove channel_dir, because we've created it
            shutil.rmtree(service_dir)
            raise

    def _init_or_update_service_from_metadata(self, metadata):
        tmp_dir = tempfile.mkdtemp()
        shutil.rmtree(tmp_dir)
        self._init_new_service_from_metadata(tmp_dir, metadata)

        service_dir = self.get_service_spec_dir(self.args.org_id, self.args.service_id)
        # it is relatevely safe to remove service_dir because we know that service_dir = self.get_service_spec_dir() so it is not a normal dir
        if (os.path.exists(service_dir)):
            shutil.rmtree(service_dir)
        shutil.move(tmp_dir, service_dir)

    def _init_channel_dir(self, channel_id, channel_info):
        channel_dir = self.get_channel_dir(self.args.org_id, self.args.service_id, channel_id)
        if (not os.path.exists(channel_dir)):
            os.makedirs(channel_dir, mode=0o700)
        # save channel info
        self._save_channel_info(channel_dir, channel_info)

    def _check_channel_is_mine(self, channel):
        if (channel["sender"].lower() != self.ident.address.lower() and
            channel["signer"].lower() != self.ident.address.lower()):
                raise Exception("Channel does not correspond to the current Ethereum identity " +
                                 "(address=%s sender=%s signer=%s)"%(self.ident.address.lower(), channel["sender"].lower(), channel["signer"].lower()))

    def _init_channel_from_metadata(self, metadata):
        channel_id = self.args.channel_id
        channel = self._get_channel_state_from_blockchain(channel_id)
        self._check_channel_is_mine(channel)
        group = metadata.get_group_by_group_id(channel["groupId"])
        if (group is None):
            group_id_base64 = base64.b64encode(channel["groupId"]).decode('ascii')
            raise Exception("Channel %i does not correspond to the given metadata.\n"%channel_id +
                             "We can't find the following group_id in metadata: " + group_id_base64)
        self._printout("#group_name")
        self._printout(group["group_name"])
        self._init_or_update_service_from_metadata(metadata)
        self._init_channel_dir(channel_id, channel)

    def init_channel_from_metadata(self):
        metadata  = load_mpe_service_metadata(self.args.metadata_file)
        self._init_channel_from_metadata(metadata)

    def init_channel_from_registry(self):
        metadata      = self._get_service_metadata_from_registry()
        self._init_channel_from_metadata(metadata)

    def _get_expiration_from_args(self):
        """
        read expiration from args.
        We allow the following types of expirations
         1. "<int>" simple integer defines absolute expiration in blocks
         2. "+<int>blocks", where <int> is integer sets expiration as: current_block + <int>
         3. "+<int>days", where <int> is integer sets expiration as: current_block + <int>*4*60*24 (we assume 15 sec/block here)

        If expiration > current_block + 1036800 (~6 month) we generate an exception if "--force" flag haven't been set
        """
        current_block = self.ident.w3.eth.blockNumber
        s = self.args.expiration
        if (s.startswith("+") and s.endswith("days")):
            rez = current_block + int(s[1:-4]) * 4 * 60 * 24
        elif (s.startswith("+") and s.endswith("blocks")):
            rez = current_block + int(s[1:-6])
        else:
            rez = int(s)
        if (rez > current_block + 1036800 and not self.args.force):
            d = (rez - current_block) // (4 * 60 * 24)
            raise Exception("You try to set expiration time too far in the future: approximately %i days. "%d +
                            "Set --force parameter if your really want to do it.")
        return rez

    def _open_channel_for_service(self, metadata):
        mpe_cogs = self.call_contract_command("MultiPartyEscrow",    "balances",  [self.ident.address])
        if (mpe_cogs < self.args.amount):
            raise Exception("insufficient funds. You MPE balance is %s AGI "%cogs2stragi(mpe_cogs))

        group_id    = metadata.get_group_id(self.args.group_name)
        recipient   = metadata.get_payment_address(self.args.group_name)

        signer = self.get_address_from_arg_or_ident(self.args.signer)

        channel_info = {"sender": self.ident.address, "signer": signer, "recipient": recipient, "groupId" : group_id}
        expiration = self._get_expiration_from_args()
        params = [channel_info["signer"], channel_info["recipient"], channel_info["groupId"], self.args.amount, expiration]
        rez = self.transact_contract_command("MultiPartyEscrow", "openChannel", params)

        if (len(rez[1]) != 1 or rez[1][0]["event"] != "ChannelOpen"):
            raise Exception("We've expected only one ChannelOpen event after openChannel. Make sure that you use correct MultiPartyEscrow address")
        return rez[1][0]["args"]["channelId"], channel_info

    def _find_already_opened_channel(self, metadata):
        sender = self.ident.address
        signer = self.get_address_from_arg_or_ident(self.args.signer)
        group_id  = metadata.get_group_id(self.args.group_name)
        recipient = metadata.get_group(self.args.group_name)["payment_address"]

        channels_ids = self._get_all_channels_filter_sender_recipient_group(sender, recipient, group_id)
        for i in channels_ids:
            channel = self._get_channel_state_from_blockchain(i)
            if (channel["signer"].lower() == signer.lower()):
                return i, channel
        return None, None

    def _open_init_channel_from_metadata(self, metadata):

        # first we simply try to initialize service without open channel (we check metadata and we compile .proto files) """
        tmp_dir = tempfile.mkdtemp()
        shutil.rmtree(tmp_dir)
        self._init_new_service_from_metadata(tmp_dir, metadata)
        shutil.rmtree(tmp_dir)

        # first we try to find channel for this service
        if (not self.args.open_new_anyway):
            channel_id, channel_info = self._find_already_opened_channel(metadata)
        if (not self.args.open_new_anyway and channel_id is not None):
            self._printout("Channel with given sender, signer and group_id is already exists we simply initialize it (channel_id = %i)"%channel_id)
            self._printout("Please run 'snet channel extend-add %i --expiration <EXPIRATION> --amount <AMOUNT>' if necessary"%channel_id)
        else:
            # open payment channel
            channel_id, channel_info = self._open_channel_for_service(metadata)
            self._printout("#channel_id")
            self._printout(channel_id)

        # initialize new channel
        self._init_or_update_service_from_metadata(metadata)
        self._init_channel_dir(channel_id, channel_info)

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

    def channel_claim_timeout_all(self):
        channels_ids = self._get_all_channels_filter_sender(self.ident.address)
        for channel_id in channels_ids:
            rez = self._get_channel_state_from_blockchain(channel_id)
            if (rez["value"] > 0 and rez["expiration"] < self.ident.w3.eth.blockNumber):
                self.transact_contract_command("MultiPartyEscrow", "channelClaimTimeout", [channel_id])

    def channel_extend_and_add_funds(self):
        expiration = self._get_expiration_from_args()
        self.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [self.args.channel_id, expiration, self.args.amount])

    def channel_extend_and_add_funds_for_service(self):
        expiration = self._get_expiration_from_args()
        channels = self._get_initialized_channels_for_service(self.args.org_id, self.args.service_id)
        channels = [c for c in channels if c["sender"].lower() == self.ident.address.lower()]
        if (len(channels) == 0):
            raise Exception("Cannot find initialized channel for service with org_id=%s service_id=%s and sender=%s"%(self.args.org_id, self.args.service_id, self.ident.adress))
        if (len(channels) > 1):
            channel_ids = [channel["channelId"] for channel in channels]
            raise Exception("We have several initialized channel: %s. You should use 'snet channel extend-add' for selected channel"%str(channel_ids))
        channel_id = channels[0]["channelId"]
        self.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [channel_id, expiration, self.args.amount])

    def _get_all_initialized_channels(self):
        """ return dict of lists  rez[(<org_id>, <service_id>)] = [(channel_id, channel_info)] """
        channels_dict = defaultdict(list)

        for channel_dir in self._get_persistent_mpe_dir().glob("*/*/*/*"):
            if (channel_dir.name.isdigit() and channel_dir.parent.name == "channels"):
                org_id = channel_dir.parent.parent.parent.name
                service_id = channel_dir.parent.parent.name
                channel_id    = int(channel_dir.name)
                channel_info  = self._read_channel_info(org_id, service_id, channel_id)
                channels_dict[(org_id, service_id)].append(channel_info)
        return channels_dict

    def _get_initialized_channels_for_service(self, org_id, service_id):
        channels = []
        for channel_dir in self._get_service_base_dir(org_id, service_id).glob("*/*"):
            if (channel_dir.name.isdigit() and channel_dir.parent.name == "channels"):
                channel_id    = int(channel_dir.name)
                channel_info  = self._read_channel_info(org_id, service_id, channel_id)
                channels.append(channel_info)
        return channels

    def _get_channel_state_from_blockchain(self, channel_id):
        abi         = get_contract_def("MultiPartyEscrow")
        channel_abi = abi_get_element_by_name(abi, "channels")
        channel     = self.call_contract_command("MultiPartyEscrow",  "channels", [channel_id])
        channel     = abi_decode_struct_to_dict(channel_abi, channel)
        return channel

    def _read_metadata_for_service(self, org_id, service_id):
        sdir = self.get_service_spec_dir(org_id, service_id)
        if (not os.path.exists(sdir)):
            raise Exception("Service with org_id=%s and service_id=%s is not initialized"%(org_id, service_id))
        return load_mpe_service_metadata(sdir.joinpath("service_metadata.json"))

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

    def _print_channels_dict_from_blockchain(self, channels_dict):
        # print only caption
        if (self.args.only_id):
            self._printout("#organization_id service_id channelId")
        else:
            self._printout("#organization_id service_id group_name channel_id nonce value(AGI) expiration(blocks)")
        for org_id, service_id in channels_dict:
            channels = self._filter_channels_sender_or_signer(channels_dict[org_id, service_id])
            metadata = self._read_metadata_for_service(org_id, service_id)
            for channel in channels:
                channel_id = channel["channelId"]
                group = metadata.get_group_by_group_id(channel["groupId"])
                if (group is None):
                    group_name = "UNDIFINED"
                else:
                    group_name = group["group_name"]
                if (self.args.only_id):
                    self._printout("%s %s %s %i"%(org_id, service_id, group_name, channel_id))
                else:
                    channel_blockchain = self._get_channel_state_from_blockchain(channel_id)
                    value_agi  = cogs2stragi(channel_blockchain["value"])
                    self._printout("%s %s %s %i %i %s %i"%(org_id, service_id, group_name, channel_id, channel_blockchain["nonce"], value_agi, channel_blockchain["expiration"]))

    def _filter_channels_sender_or_signer(self, channels):
        good_channels = []
        for channel in channels:
            not_sender = channel["sender"] != self.ident.address
            not_signer = channel["signer"] != self.ident.address
            if (self.args.filter_sender and not_sender):
                continue
            if (self.args.filter_signer and not_signer):
                continue
            if (self.args.filter_my and not_sender and not_signer):
                continue
            good_channels.append(channel)
        return good_channels

    def print_initialized_channels(self):
        channels_dict = self._get_all_initialized_channels()
        self._print_channels_dict_from_blockchain(channels_dict)

    def print_initialized_channels_filter_service(self):
        channels = self._get_initialized_channels_for_service(self.args.org_id, self.args.service_id)
        self._print_channels_dict_from_blockchain({(self.args.org_id, self.args.service_id):channels})

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
        channels_ids = self._get_all_channels_filter_sender(address)
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
        address        = self.get_address_from_arg_or_ident(self.args.sender)
        address_padded = pad_hex(address.lower(), 256)
        metadata = self._get_service_metadata_from_registry()
        group_id = metadata.get_group_id(self.args.group_name)
        group_id_hex = "0x" + group_id.hex()
        channels_ids = self._get_all_filtered_channels([address_padded, None, group_id_hex])
        self._print_channels_from_blockchain(channels_ids)

    def _get_all_channels_filter_sender(self, sender):
        sender_padded = pad_hex(sender.lower(), 256)
        channels_ids = self._get_all_filtered_channels([sender_padded])
        return channels_ids

    def _get_all_channels_filter_sender_recipient_group(self, sender, recipient, group_id):
        sender_padded    = pad_hex(sender.lower(),    256)
        recipient_padded = pad_hex(recipient.lower(), 256)
        group_id_hex = "0x" + group_id.hex()
        return self._get_all_filtered_channels([sender_padded, recipient_padded, group_id_hex])

    #Auxilary functions
    def print_block_number(self):
         self._printout(self.ident.w3.eth.blockNumber)
