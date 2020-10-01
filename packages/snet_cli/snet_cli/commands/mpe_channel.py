import base64
import os
import pickle
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

from snet.snet_cli.metadata.service import mpe_service_metadata_from_json, load_mpe_service_metadata
from snet.snet_cli.metadata.organization import OrganizationMetadata
from snet.snet_cli.utils.ipfs_utils import safe_extract_proto_from_ipfs, get_from_ipfs_and_checkhash, bytesuri_to_hash
from snet.snet_cli.utils.utils import compile_proto, get_contract_def, abi_get_element_by_name, \
    abi_decode_struct_to_dict, \
    type_converter
from snet_cli.commands.commands import OrganizationCommand
from snet_cli.utils.agi2cogs import cogs2stragi
from web3.utils.encoding import pad_hex
from web3.utils.events import get_event_data


# we inherit MPEServiceCommand because we need _get_service_metadata_from_registry
class MPEChannelCommand(OrganizationCommand):

    def _get_persistent_mpe_dir(self):
        """ get persistent storage for mpe """
        mpe_address = self.get_mpe_address().lower()
        registry_address = self.get_registry_address().lower()
        return Path.home().joinpath(".snet", "mpe_client", "%s_%s" % (mpe_address, registry_address))

    def _get_service_base_dir(self, org_id, service_id):
        """ get persistent storage for the given service (~/.snet/mpe_client/<mpe_address>_<registry_address>/<org_id>/<service_id>/) """
        return self._get_persistent_mpe_dir().joinpath(org_id, service_id)

    def get_service_spec_dir(self, org_id, service_id):
        """ get persistent storage for the given service (~/.snet/mpe_client/<mpe_address>/<org_id>/<service_id>/service/) """
        return self._get_service_base_dir(org_id, service_id).joinpath("service")

    def _get_service_info_file(self, org_id, service_id):
        return os.path.join(self._get_service_base_dir(org_id, service_id), "service_info.pickle")

    def _save_service_info(self, org_id, service_id, service_info):
        fn = self._get_service_info_file(org_id, service_id)
        pickle.dump(service_info, open(fn, "wb"))

    def _read_service_info(self, org_id, service_id):
        fn = self._get_service_info_file(org_id, service_id)
        return pickle.load(open(fn, "rb"))

    def is_service_initialized(self):
        return os.path.isfile(self._get_service_info_file(self.args.org_id, self.args.service_id))

    def _get_org_base_dir(self, org_id):
        """ get persistent storage for the given service (~/.snet/mpe_client/<mpe_address>_<registry_address>/<org_id>/) """
        return self._get_persistent_mpe_dir().joinpath(org_id)
    #

    def get_org_spec_dir(self, org_id):
        """ get persistent storage for the given service (~/.snet/mpe_client/<mpe_address>/<org_id>/) """
        return self._get_org_base_dir(org_id)

    def _get_channels_info_file(self, org_id):
        return os.path.join(self._get_org_base_dir(org_id), "channels_info.pickle")

    def _get_service_metadata(self):
        service_dir = self.get_service_spec_dir(
            self.args.org_id, self.args.service_id)
        service_metadata = load_mpe_service_metadata(
            os.path.join(service_dir, "service_metadata.json"))
        return service_metadata

    def _add_channel_to_initialized(self, org_id, channel):
        channels_dict = self._get_initialized_channels_dict_for_org(org_id)
        channels_dict[channel["channelId"]] = channel

        # replace old file atomically (os.rename is more or less atomic)
        tmp = tempfile.NamedTemporaryFile(delete=False)
        pickle.dump(channels_dict, open(tmp.name, "wb"))
        shutil.move(tmp.name, self._get_channels_info_file(org_id))

    def _get_initialized_channels_dict_for_org(self, org_id):
        '''return {channel_id: channel}'''
        fn = self._get_channels_info_file(org_id)
        if (os.path.isfile(fn)):
            return pickle.load(open(fn, "rb"))
        else:
            return {}

    def _get_initialized_channels_for_org(self, org_id):
        '''return [channel]'''
        channels_dict = self._get_initialized_channels_dict_for_org(org_id)
        return list(channels_dict.values())

    def _get_org_info_file(self, org_id):
        return os.path.join(self._get_org_base_dir(org_id), "org_info.pickle")

    def _save_org_info(self, org_id, org_info):
        fn = self._get_org_info_file(org_id)
        pickle.dump(org_info, open(fn, "wb"))

    def _read_org_info(self, org_id):
        fn = self._get_org_info_file(org_id)
        return pickle.load(open(fn, "rb"))

    def is_org_initialized(self):
        return os.path.isfile(self._get_org_info_file(self.args.org_id))

    def _check_mpe_address_metadata(self, metadata):
        """ we make sure that MultiPartyEscrow address from metadata is correct """
        mpe_address = self.get_mpe_address()
        if (str(mpe_address).lower() != str(metadata["mpe_address"]).lower()):
            raise Exception("MultiPartyEscrow contract address from metadata %s do not correspond to current MultiPartyEscrow address %s" % (
                metadata["mpe_address"], mpe_address))

    def _init_or_update_org_if_needed(self, metadata, org_registration):
        # if service was already initialized and metadataURI hasn't changed we do nothing
        if self.is_org_initialized():
            if self.is_metadataURI_has_changed(org_registration):
                self._printerr("# Organization with org_id=%s " %
                               (self.args.org_id))
                self._printerr(
                    "# ATTENTION!!! price or other paramaters might have been changed!\n")
            else:
                return  # we do nothing
        self._printerr("# Initilize service with org_id=%s" %
                       (self.args.org_id))
        # self._check_mpe_address_metadata(metadata)
        org_dir = self.get_org_spec_dir(self.args.org_id)

        if (not os.path.exists(org_dir)):
            os.makedirs(org_dir, mode=0o700)

        try:
            # save orgainzaiton_metadata.json in channel_dir
            metadata.save_pretty(os.path.join(
                org_dir, "organization_metadata.json"))
        except:
            # it is secure to remove channel_dir, because we've created it
            # shutil.rmtree(org_dir)
            raise
        self._save_org_info(self.args.org_id, org_registration)

    def _init_or_update_registered_org_if_needed(self):
        '''
        similar to _init_or_update_org_if_needed but we get organization_registraion from registry,
        so we can update only registered organization
        '''
        if (self.is_org_initialized()):
            old_reg = self._read_org_info(self.args.org_id)

            # metadataURI will be in old_reg only for service which was initilized from registry (not from metadata)
            # we do nothing for services which were initilized from metadata
            if ("orgMetadataURI" not in old_reg):
                return
            org_registration = self._get_organization_registration(
                self.args.org_id)
            # if metadataURI hasn't been changed we do nothing
            if (not self.is_metadataURI_has_changed(org_registration)):
                return
        else:
            org_registration = self._get_organization_registration(
                self.args.org_id)

        org_metadata = self._get_organization_metadata_from_registry(
            self.args.org_id)
        self._init_or_update_org_if_needed(org_metadata, org_registration)

    def is_metadataURI_has_changed(self, new_reg):
        old_reg = self._read_org_info(self.args.org_id)
        return new_reg.get("orgMetadataURI") != old_reg.get("orgMetadataURI")

    def is_service_metadataURI_has_changed(self, new_reg):
        old_reg = self._read_service_info(
            self.args.org_id, self.args.service_id)
        return new_reg.get("metadataURI") != old_reg.get("metadataURI")

    def _check_channel_is_mine(self, channel):
        if (channel["sender"].lower() != self.ident.address.lower() and
                channel["signer"].lower() != self.ident.address.lower()):
            raise Exception("Channel does not correspond to the current Ethereum identity " +
                            "(address=%s sender=%s signer=%s)" % (self.ident.address.lower(), channel["sender"].lower(), channel["signer"].lower()))

    def _init_channel_from_metadata(self, metadata, org_registration):
        channel_id = self.args.channel_id
        channel = self._get_channel_state_from_blockchain(channel_id)
        self._check_channel_is_mine(channel)
        group_id = metadata.get_group_id_by_group_name(self.args.group_name)
        if (group_id is None):

            raise Exception("Channel %i does not correspond to the given metadata.\n" % channel_id +
                            "We can't find the following group_id in metadata: " + self.args.group_name)

        self._printout("#group_name")
        # self._printout(group.group_name)
        self._init_or_update_org_if_needed(metadata, org_registration)
        self._add_channel_to_initialized(self.args.org_id, channel)

    def init_channel_from_metadata(self):
        metadata = OrganizationMetadata.from_file(self.args.metadata_file)
        self._init_channel_from_metadata(metadata, {})

    def init_channel_from_registry(self):
        metadata = self._get_organization_metadata_from_registry(
            self.args.org_id)
        org_registration = self._get_organization_registration(
            self.args.org_id)
        self._init_channel_from_metadata(metadata, org_registration)

    def _expiration_str_to_blocks(self, expiration_str, current_block):
        s = expiration_str
        if (s.startswith("+") and s.endswith("days")):
            rez = current_block + int(s[1:-4]) * 4 * 60 * 24
        elif (s.startswith("+") and s.endswith("blocks")):
            rez = current_block + int(s[1:-6])
        else:
            rez = int(s)
        return rez

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

        rez = self._expiration_str_to_blocks(
            self.args.expiration, current_block)
        if (rez > current_block + 1036800 and not self.args.force):
            d = (rez - current_block) // (4 * 60 * 24)
            raise Exception("You try to set expiration time too far in the future: approximately %i days. " % d +
                            "Set --force parameter if your really want to do it.")
        return rez

    def _open_channel_for_org(self, metadata):
        mpe_cogs = self.call_contract_command(
            "MultiPartyEscrow",    "balances",  [self.ident.address])
        if (mpe_cogs < self.args.amount):
            raise Exception(
                "insufficient funds. You MPE balance is %s AGI " % cogs2stragi(mpe_cogs))

        group_id = base64.b64decode(
            metadata.get_group_id_by_group_name(self.args.group_name))
        if not group_id:
            raise Exception(
                "group  %s is associated with organization", self.args.group_name)

        recipient = metadata.get_payment_address_for_group(
            self.args.group_name)

        signer = self.get_address_from_arg_or_ident(self.args.signer)

        channel_info = {"sender": self.ident.address, "signer": signer,
                        "recipient": recipient, "groupId": group_id}
        expiration = self._get_expiration_from_args()
        params = [channel_info["signer"], channel_info["recipient"],
                  channel_info["groupId"], self.args.amount, expiration]
        rez = self.transact_contract_command(
            "MultiPartyEscrow", "openChannel", params)

        if (len(rez[1]) != 1 or rez[1][0]["event"] != "ChannelOpen"):
            raise Exception(
                "We've expected only one ChannelOpen event after openChannel. Make sure that you use correct MultiPartyEscrow address")

        channel_info["channelId"] = rez[1][0]["args"]["channelId"]
        return channel_info

    def _initialize_already_opened_channel(self, metadata, sender, signer):

        group_id = base64.b64decode(
            metadata.get_group_id_by_group_name(self.args.group_name))
        recipient = metadata.get_payment_address_for_group(
            self.args.group_name)
        channels_ids = self._get_all_channels_filter_sender_recipient_group(
            sender, recipient, group_id)
        for i in sorted(channels_ids):
            channel = self._get_channel_state_from_blockchain(i)
            if (channel["signer"].lower() == signer.lower()):
                self._printerr(
                    "# Channel with given sender, signer and group_id is already exists we simply initialize it (channel_id = %i)" % channel["channelId"])
#                self._printerr("# Please run 'snet channel extend-add %i --expiration <EXPIRATION> --amount <AMOUNT>' if necessary"%channel["channelId"])
                self._add_channel_to_initialized(self.args.org_id, channel)
                return channel
        return None

    def _open_init_channel_from_metadata(self, metadata, org_registration):
        self._init_or_update_org_if_needed(metadata, org_registration)

        # Before open new channel we try to find already openned channel
        if (not self.args.open_new_anyway):
            sender = self.ident.address
            signer = self.get_address_from_arg_or_ident(self.args.signer)
            channel = self._initialize_already_opened_channel(
                metadata, sender, signer)
            if (channel is not None):
                return

        # open payment channel
        channel = self._open_channel_for_org(metadata)
        self._printout("#channel_id")
        self._printout(channel["channelId"])

        # initialize channel
        self._add_channel_to_initialized(self.args.org_id, channel)

    def open_init_channel_from_metadata(self):
        metadata = OrganizationMetadata.from_file(self.args.metadata_file)
        self._open_init_channel_from_metadata(metadata, {})

    def open_init_channel_from_registry(self):
        metadata = self._get_organization_metadata_from_registry(
            self.args.org_id)
        org_registration = self._get_organization_registration(
            self.args.org_id)
        self._open_init_channel_from_metadata(metadata, org_registration)

    def channel_claim_timeout(self):
        rez = self._get_channel_state_from_blockchain(self.args.channel_id)
        if (rez["value"] == 0):
            raise Exception("Channel has 0 value. There is nothing to claim")
        self.transact_contract_command(
            "MultiPartyEscrow", "channelClaimTimeout", [self.args.channel_id])

    def channel_claim_timeout_all(self):
        channels_ids = self._get_all_channels_filter_sender(self.ident.address)
        for channel_id in channels_ids:
            rez = self._get_channel_state_from_blockchain(channel_id)
            if (rez["value"] > 0 and rez["expiration"] < self.ident.w3.eth.blockNumber):
                self.transact_contract_command(
                    "MultiPartyEscrow", "channelClaimTimeout", [channel_id])

    def _channel_extend_add_funds_with_channel_id(self, channel_id):
        if (self.args.amount is None and self.args.expiration is None):
            raise Exception("You should specify --amount or/and --expiration")

        # only add funds to the channel (if --expiration hasn't been specified)
        if (self.args.expiration is None):
            self.transact_contract_command("MultiPartyEscrow", "channelAddFunds", [
                                           channel_id, self.args.amount])
            return

        expiration = self._get_expiration_from_args()
        self.check_new_expiration_from_blockchain(channel_id, expiration)
        # only extend channel (if --amount hasn't been specified)
        if (self.args.amount is None):
            self.transact_contract_command("MultiPartyEscrow", "channelExtend", [
                                           channel_id, expiration])
            return

        # extend and add funds if --amount and --expiration have been specified
        self.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [
                                       channel_id, expiration, self.args.amount])

    def channel_extend_and_add_funds(self):
        self._channel_extend_add_funds_with_channel_id(self.args.channel_id)

    def check_new_expiration_from_blockchain(self, channel_id, new_expiration):
        channel = self._get_channel_state_from_blockchain(channel_id)
        if (new_expiration < channel["expiration"]):
            raise Exception("New expiration (%i) is smaller then old one (%i)" % (
                new_expiration, channel["expiration"]))

    def _smart_get_initialized_channel_for_org(self, metadata, filter_by, is_try_initailize=True):
        '''
         - filter_by can be sender or signer
        '''
        channels = self._get_initialized_channels_for_org(self.args.org_id)
        group_id = base64.b64decode(
            metadata.get_group_id_by_group_name(self.args.group_name))
        channels = [c for c in channels if c[filter_by].lower(
        ) == self.ident.address.lower() and c["groupId"] == group_id]

        if (len(channels) == 0 and is_try_initailize):
            # this will work only in simple case where signer == sender
            self._initialize_already_opened_channel(
                metadata, self.ident.address, self.ident.address)
            return self._smart_get_initialized_channel_for_org(metadata, filter_by, is_try_initailize=False)

        if (len(channels) == 0):
            raise Exception("Cannot find initialized channel for service with org_id=%s service_id=%s and signer=%s" % (
                self.args.org_id, self.args.service_id, self.ident.address))
        if (self.args.channel_id is None):
            if (len(channels) > 1):
                channel_ids = [channel["channelId"] for channel in channels]
                raise Exception(
                    "We have several initialized channel: %s. You should use --channel-id to select one" % str(channel_ids))
            return channels[0]
        for channel in channels:
            if (channel["channelId"] == self.args.channel_id):
                return channel
        raise Exception(
            "Channel %i has not been initialized or your are not the sender/signer of it" % self.args.channel_id)

    def _smart_get_channel_for_org(self):
        self._init_or_update_registered_org_if_needed()
        metadata = self._read_metadata_for_org(self.args.org_id)
        return self._smart_get_initialized_channel_for_org(metadata, "sender")

    def channel_extend_and_add_funds_for_org(self):
        channel_id = self._smart_get_channel_for_org()["channelId"]
        self._channel_extend_add_funds_with_channel_id(channel_id)

    def _get_all_initialized_channels(self):
        """ return dict of lists  rez[(<org_id>, <service_id>)] = [(channel_id, channel_info)] """
        channels_dict = defaultdict(list)
        for service_base_dir in self._get_persistent_mpe_dir().glob("*/*"):
            org_id = service_base_dir.parent.name
            channels = self._get_initialized_channels_for_org(org_id)
            if (channels):
                channels_dict[org_id] = channels
        return channels_dict

    def _get_channel_state_from_blockchain(self, channel_id):
        abi = get_contract_def("MultiPartyEscrow")
        channel_abi = abi_get_element_by_name(abi, "channels")
        channel = self.call_contract_command(
            "MultiPartyEscrow",  "channels", [channel_id])
        channel = abi_decode_struct_to_dict(channel_abi, channel)
        channel["channelId"] = channel_id
        return channel

    def _read_metadata_for_org(self, org_id):
        sdir = self.get_org_spec_dir(org_id)
        if (not os.path.exists(sdir)):
            raise Exception(
                "Service with org_id=%s is not initialized" % (org_id))
        return OrganizationMetadata.from_file(sdir.joinpath("organization_metadata.json"))

    def _print_channels_from_blockchain(self, channels_ids):
        channels_ids = sorted(channels_ids)
        if (self.args.only_id):
            self._printout("#channelId")
            [self._printout(str(i)) for i in channels_ids]
            return
        self._printout(
            "#channelId nonce recipient groupId(base64) value(AGI) expiration(blocks)")
        for i in channels_ids:
            channel = self._get_channel_state_from_blockchain(i)
            value_agi = cogs2stragi(channel["value"])
            group_id_base64 = base64.b64encode(
                channel["groupId"]).decode("ascii")
            self._printout("%i %i %s %s %s %i" % (i, channel["nonce"], channel["recipient"], group_id_base64,
                                                  value_agi, channel["expiration"]))

    def _print_channels_dict_from_blockchain(self, channels_dict):
        # print only caption
        if (self.args.only_id):
            self._printout("#organization_id service_id channelId")
        else:
            self._printout(
                "#organization_id service_id group_name channel_id nonce value(AGI) expiration(blocks)")
        for org_id in channels_dict:
            channels = self._filter_channels_sender_or_signer(
                channels_dict[org_id])
            metadata = self._read_metadata_for_org(org_id)
            for channel in channels:
                channel_id = channel["channelId"]
                group_id_base64 = base64.b64encode(
                    channel["groupId"]).decode('ascii')
                group = metadata.get_group_by_group_id(group_id_base64)
                if (group is None):
                    group_name = "UNDIFINED"
                else:
                    group_name = group.group_name
                if (self.args.only_id):
                    self._printout("%s %s %i" %
                                   (org_id, group_name, channel_id))
                else:
                    channel_blockchain = self._get_channel_state_from_blockchain(
                        channel_id)
                    value_agi = cogs2stragi(channel_blockchain["value"])
                    self._printout("%s %s %i %i %s %i" % (org_id, group_name, channel_id,
                                                          channel_blockchain["nonce"], value_agi, channel_blockchain["expiration"]))

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

    def print_initialized_channels_filter_org(self):
        channels = self._get_initialized_channels_for_org(self.args.org_id)
        self._print_channels_dict_from_blockchain({self.args.org_id: channels})

    def _get_all_filtered_channels(self, topics_without_signature):
        """ get all filtered chanels from blockchain logs """
        mpe_address = self.get_mpe_address()
        event_signature = self.ident.w3.sha3(
            text="ChannelOpen(uint256,uint256,address,address,address,bytes32,uint256,uint256)").hex()
        topics = [event_signature] + topics_without_signature
        logs = self.ident.w3.eth.getLogs(
            {"fromBlock": self.args.from_block, "address": mpe_address, "topics": topics})
        abi = get_contract_def("MultiPartyEscrow")
        event_abi = abi_get_element_by_name(abi, "ChannelOpen")
        channels_ids = [get_event_data(event_abi, l)[
            "args"]["channelId"] for l in logs]
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
        channels_ids = self._get_all_filtered_channels([None, address_padded])
        self._print_channels_from_blockchain(channels_ids)

    def print_all_channels_filter_group(self):
        metadata = self._get_organization_metadata_from_registry(
            self.args.org_id)
        group_id = base64.b64decode(
            metadata.get_group_id_by_group_name(self.args.group_name))
        group_id_hex = "0x" + group_id.hex()
        channels_ids = self._get_all_filtered_channels(
            [None, None, group_id_hex])
        self._print_channels_from_blockchain(channels_ids)

    def print_all_channels_filter_group_sender(self):
        address = self.get_address_from_arg_or_ident(self.args.sender)
        address_padded = pad_hex(address.lower(), 256)
        metadata = self._get_organization_metadata_from_registry(
            self.args.org_id)
        group_id = base64.b64decode(
            metadata.get_group_id_by_group_name(self.args.group_name))
        group_id_hex = "0x" + group_id.hex()
        channels_ids = self._get_all_filtered_channels(
            [address_padded, None, group_id_hex])
        self._print_channels_from_blockchain(channels_ids)

    def _get_all_channels_filter_sender(self, sender):
        sender_padded = pad_hex(sender.lower(), 256)
        channels_ids = self._get_all_filtered_channels([sender_padded])
        return channels_ids

    def _get_all_channels_filter_sender_recipient_group(self, sender, recipient, group_id):
        sender_padded = pad_hex(sender.lower(),    256)
        recipient_padded = pad_hex(recipient.lower(), 256)
        group_id_hex = "0x" + group_id.hex()
        return self._get_all_filtered_channels([sender_padded, recipient_padded, group_id_hex])

    # Auxilary functions
    def print_block_number(self):
        self._printout(self.ident.w3.eth.blockNumber)

    def _get_service_registration(self):
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id)]
        rez = self.call_contract_command(
            "Registry", "getServiceRegistrationById", params)
        if (rez[0] == False):
            raise Exception("Cannot find Service with id=%s in Organization with id=%s" % (
                self.args.service_id, self.args.org_id))
        return {"metadataURI": rez[2], "tags": rez[3]}

    def _get_service_metadata_from_registry(self):
        rez = self._get_service_registration()
        metadata_hash = bytesuri_to_hash(rez["metadataURI"])
        metadata = get_from_ipfs_and_checkhash(
            self._get_ipfs_client(), metadata_hash)
        metadata = metadata.decode("utf-8")
        metadata = mpe_service_metadata_from_json(metadata)
        return metadata

    def _init_or_update_service_if_needed(self, metadata, service_registration):
        # if service was already initialized and metadataURI hasn't changed we do nothing
        if self.is_service_initialized():
            if self.is_service_metadataURI_has_changed(service_registration):
                self._printerr("# Service with org_id=%s and service_id=%s was updated" % (
                    self.args.org_id, self.args.service_id))
                self._printerr(
                    "# ATTENTION!!! price or other paramaters might have been changed!\n")
            else:
                return  # we do nothing
        self._printerr("# Initilize service with org_id=%s and service_id=%s" % (
            self.args.org_id, self.args.service_id))
        self._check_mpe_address_metadata(metadata)
        service_dir = self.get_service_spec_dir(
            self.args.org_id, self.args.service_id)

        # remove old service_dir
        # it is relatevely safe to remove service_dir because we know that service_dir = self.get_service_spec_dir() so it is not a normal dir
        if (os.path.exists(service_dir)):
            shutil.rmtree(service_dir)

        os.makedirs(service_dir, mode=0o700)
        try:
            spec_dir = os.path.join(service_dir, "service_spec")
            os.makedirs(spec_dir, mode=0o700)
            safe_extract_proto_from_ipfs(
                self._get_ipfs_client(), metadata["model_ipfs_hash"], spec_dir)

            # compile .proto files
            if (not compile_proto(Path(spec_dir), service_dir)):
                raise Exception("Fail to compile %s/*.proto" % spec_dir)

            # save service_metadata.json in channel_dir
            metadata.save_pretty(os.path.join(
                service_dir, "service_metadata.json"))
        except Exception as e:
            # it is secure to remove channel_dir, because we've created it
            print(e)
            shutil.rmtree(service_dir)
            raise
        self._save_service_info(
            self.args.org_id, self.args.service_id, service_registration)

    def _init_or_update_registered_service_if_needed(self):
        '''
        similar to _init_or_update_service_if_needed but we get service_registraion from registry,
        so we can update only registered services
        '''
        if (self.is_service_initialized()):
            old_reg = self._read_service_info(
                self.args.org_id, self.args.service_id)

            # metadataURI will be in old_reg only for service which was initilized from registry (not from metadata)
            # we do nothing for services which were initilized from metadata
            if ("metadataURI" not in old_reg):
                return

            service_registration = self._get_service_registration()
            # if metadataURI hasn't been changed we do nothing
            if (not self.is_service_metadataURI_has_changed(service_registration)):
                return
        else:
            service_registration = self._get_service_registration()

        service_metadata = self._get_service_metadata_from_registry()
        self._init_or_update_service_if_needed(
            service_metadata, service_registration)
