import base64
import os
import pickle
import shutil
import tempfile
from collections import defaultdict
from importlib.metadata import metadata
from pathlib import Path

from eth_abi.codec import ABICodec
from web3._utils.events import get_event_data
from snet.contracts import get_contract_def, get_contract_deployment_block

from snet.cli.commands.commands import OrganizationCommand
from snet.cli.metadata.service import mpe_service_metadata_from_json, load_mpe_service_metadata
from snet.cli.metadata.organization import OrganizationMetadata
from snet.cli.utils.agix2cogs import cogs2stragix
from snet.cli.utils.ipfs_utils import get_from_ipfs_and_checkhash
from snet.cli.utils.utils import abi_decode_struct_to_dict, abi_get_element_by_name, \
    compile_proto, type_converter, bytesuri_to_hash, get_file_from_filecoin, download_and_safe_extract_proto


# we inherit MPEServiceCommand because we need _get_service_metadata_from_registry
class MPEChannelCommand(OrganizationCommand):

    def _get_persistent_mpe_dir(self):
        """ get persistent storage for mpe """
        mpe_address = self.get_mpe_address().lower()
        registry_address = self.get_registry_address().lower()
        return Path.home().joinpath(".snet", "mpe_client", "%s_%s" % (mpe_address, registry_address))

    def _get_channels_cache_file(self):
        channels_dir = Path.home().joinpath(".snet", "cache", "mpe")
        mpe_address = self.get_mpe_address().lower()
        channels_file = channels_dir.joinpath(str(mpe_address), "channels.pickle")
        return channels_file

    def _update_channels_cache(self):
        channels = []
        last_read_block = get_contract_deployment_block(self.ident.w3, "MultiPartyEscrow")
        channels_file = self._get_channels_cache_file()

        if not channels_file.exists():
            self._printout(f"Channels cache is empty. Caching may take some time when first accessing channels.\nCaching in progress...")
            channels_file.parent.mkdir(parents=True, exist_ok=True)
            with open(channels_file, "wb") as f:
                empty_dict = {
                    "last_read_block": last_read_block,
                    "channels": channels
                }
                pickle.dump(empty_dict, f)
        else:
            with open(channels_file, "rb") as f:
                load_dict = pickle.load(f)
            last_read_block = load_dict["last_read_block"]
            channels = load_dict["channels"]

        current_block_number = self.ident.w3.eth.block_number

        if last_read_block < current_block_number:
            new_channels = self._get_all_opened_channels_from_blockchain(last_read_block, current_block_number)
            channels = channels + new_channels
            last_read_block = current_block_number

            with open(channels_file, "wb") as f:
                dict_to_save = {
                    "last_read_block": last_read_block,
                    "channels": channels
                }
                pickle.dump(dict_to_save, f)

    def _get_channels_from_cache(self):
        self._update_channels_cache()
        with open(self._get_channels_cache_file(), "rb") as f:
            load_dict = pickle.load(f)
        return load_dict["channels"]

    def _event_data_args_to_dict(self, event_data):
        return {
            "channel_id": event_data["channelId"],
            "sender": event_data["sender"],
            "signer": event_data["signer"],
            "recipient": event_data["recipient"],
            "group_id": event_data["groupId"],
        }

    def _get_all_opened_channels_from_blockchain(self, starting_block_number, to_block_number):
        mpe_address = self.get_mpe_address()
        event_topics = [self.ident.w3.keccak(
            text="ChannelOpen(uint256,uint256,address,address,address,bytes32,uint256,uint256)").hex()]
        blocks_per_batch = 5000
        codec: ABICodec = self.ident.w3.codec

        logs = []
        from_block = starting_block_number
        while from_block <= to_block_number:
            to_block = min(from_block + blocks_per_batch, to_block_number)
            logs += self.ident.w3.eth.get_logs({"fromBlock": from_block,
                                                  "toBlock": to_block,
                                                  "address": mpe_address,
                                                  "topics": event_topics})
            from_block = to_block + 1

        abi = get_contract_def("MultiPartyEscrow")
        event_abi = abi_get_element_by_name(abi, "ChannelOpen")

        event_data_list = [get_event_data(codec, event_abi, l)["args"] for l in logs]
        channels_opened = list(map(self._event_data_args_to_dict, event_data_list))

        return channels_opened

    def _get_filtered_channels(self, return_only_id=False, **kwargs):
        channels = self._get_channels_from_cache()
        for key, value in kwargs.items():
            if key == "group_id":
                check_ch = lambda c: base64.b64encode(c[key]).decode("utf-8") == value
            else:
                check_ch = lambda c: c[key] == value
            channels = [ch for ch in channels if check_ch(ch)]
        if return_only_id:
            return [c["channel_id"] for c in channels]
        return channels

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
        if str(mpe_address).lower() != str(metadata["mpe_address"]).lower():
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

        if not os.path.exists(org_dir):
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
        if self.is_org_initialized():
            old_reg = self._read_org_info(self.args.org_id)

            # metadataURI will be in old_reg only for service which was initilized from registry (not from metadata)
            # we do nothing for services which were initilized from metadata
            if "orgMetadataURI" not in old_reg:
                return
            org_registration = self._get_organization_registration(
                self.args.org_id)
            # if metadataURI hasn't been changed we do nothing
            if not self.is_metadataURI_has_changed(org_registration):
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

    def _expiration_str_to_blocks(self, expiration_str, current_block):
        s = expiration_str
        if s.startswith("+") and s.endswith("days"):
            rez = current_block + int(s[1:-4]) * 4 * 60 * 24
        elif s.startswith("+") and s.endswith("blocks"):
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
        current_block = self.ident.w3.eth.block_number

        rez = self._expiration_str_to_blocks(
            self.args.expiration, current_block)
        if rez > current_block + 1036800 and not self.args.force:
            d = (rez - current_block) // (4 * 60 * 24)
            raise Exception("You try to set expiration time too far in the future: approximately %i days. " % d +
                            "Set --force parameter if your really want to do it.")
        return rez

    def _open_channel_for_org(self, metadata):

        mpe_cogs = self.call_contract_command(
            "MultiPartyEscrow",    "balances",  [self.ident.address])
        if mpe_cogs < self.args.amount:
            raise Exception(
                "insufficient funds. You MPE balance is %s AGIX " % cogs2stragix(mpe_cogs))

        group_id = base64.b64decode(metadata.get_group_id_by_group_name(self.args.group_name))
        if not group_id:
            raise Exception("group  %s is associated with organization", self.args.group_name)

        recipient = metadata.get_payment_address_for_group(self.args.group_name)

        signer = self.get_address_from_arg_or_ident(self.args.signer)

        channel_info = {"sender": self.ident.address, "signer": signer,
                        "recipient": recipient, "group_id": group_id}
        expiration = self._get_expiration_from_args()
        params = [channel_info["signer"], channel_info["recipient"],
                  channel_info["group_id"], self.args.amount, expiration]
        rez = self.transact_contract_command(
            "MultiPartyEscrow", "openChannel", params)

        if len(rez[1]) != 1 or rez[1][0]["event"] != "ChannelOpen":
            raise Exception(
                "We've expected only one ChannelOpen event after openChannel. Make sure that you use correct MultiPartyEscrow address")

        channel_info["channel_id"] = rez[1][0]["args"]["channelId"]
        return channel_info

    def _check_already_opened_channel(self, metadata, sender, signer):
        group_id = metadata.get_group_id_by_group_name(self.args.group_name)
        recipient = metadata.get_payment_address_for_group(self.args.group_name)
        channels = self._get_filtered_channels(sender=sender, recipient=recipient, group_id=group_id)

        for i in channels:
            channel = self._get_channel_state_from_blockchain(i)
            if channel["signer"].lower() == signer.lower():
                self._printerr(
                    "# Channel with given sender, signer and group_id is already exists. (channel_id = %i)"
                    % channel["channel_id"])
                return channel

        return None

    def _open_channel_from_metadata(self, metadata, org_registration):
        self._init_or_update_org_if_needed(metadata, org_registration)

        # Before open new channel we try to find already opened channel
        if not self.args.open_new_anyway:
            sender = self.ident.address
            signer = self.get_address_from_arg_or_ident(self.args.signer)
            channel = self._check_already_opened_channel(metadata, sender, signer)
            if channel is not None:
                return

        # open payment channel
        channel = self._open_channel_for_org(metadata)
        self._printout("#channel_id")
        self._printout(channel["channel_id"])

    def open_channel_from_metadata(self):
        metadata = OrganizationMetadata.from_file(self.args.metadata_file)
        self._open_channel_from_metadata(metadata, {})

    def open_channel_from_registry(self):
        metadata = self._get_organization_metadata_from_registry(
            self.args.org_id)
        org_registration = self._get_organization_registration(
            self.args.org_id)
        self._open_channel_from_metadata(metadata, org_registration)

    def channel_claim_timeout(self):
        rez = self._get_channel_state_from_blockchain(self.args.channel_id)
        if rez["expiration"] >= self.ident.w3.eth.block_number:
            raise Exception("Channel is not expired yet")
        elif rez["value"] == 0:
            raise Exception("Channel has 0 value. There is nothing to claim")
        self.transact_contract_command(
            "MultiPartyEscrow", "channelClaimTimeout", [self.args.channel_id])

    def channel_claim_timeout_all(self):
        channels_ids = self._get_filtered_channels(return_only_id=True, sender=self.ident.address)
        for channel_id in channels_ids:
            response = self._get_channel_state_from_blockchain(channel_id)
            if response["value"] > 0 and response["expiration"] < self.ident.w3.eth.block_number:
                self.transact_contract_command(
                    "MultiPartyEscrow", "channelClaimTimeout", [channel_id])

    def _channel_extend_add_funds_with_channel_id(self, channel_id):
        if self.args.amount is None and self.args.expiration is None:
            raise Exception("You should specify --amount or/and --expiration")

        # only add funds to the channel (if --expiration hasn't been specified)
        if self.args.expiration is None:
            self.transact_contract_command("MultiPartyEscrow", "channelAddFunds", [channel_id, self.args.amount])
            return

        expiration = self._get_expiration_from_args()
        self._check_new_expiration_from_blockchain(channel_id, expiration)
        # only extend channel (if --amount hasn't been specified)
        if self.args.amount is None:
            self.transact_contract_command("MultiPartyEscrow", "channelExtend", [
                                           channel_id, expiration])
            return

        # extend and add funds if --amount and --expiration have been specified
        self.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [
                                       channel_id, expiration, self.args.amount])

    def channel_extend_and_add_funds(self):
        self._channel_extend_add_funds_with_channel_id(self.args.channel_id)

    def _check_new_expiration_from_blockchain(self, channel_id, new_expiration):
        channel = self._get_channel_state_from_blockchain(channel_id)
        if new_expiration < channel["expiration"]:
            raise Exception("New expiration (%i) is smaller then old one (%i)" % (
                new_expiration, channel["expiration"]))

    def _smart_get_channel_for_org(self, metadata, filter_by):
        '''
         - filter_by can be sender or signer
        '''
        recipient = metadata.get_payment_address_for_group(self.args.group_name)
        group_id = metadata.get_group_id_by_group_name(self.args.group_name)
        channels = self._get_filtered_channels(return_only_id=False, recipient=recipient, group_id=group_id)
        channels = [c for c in channels if c[filter_by].lower() == self.ident.address.lower()]

        if len(channels) == 0:
            if self.args.service_id:
                raise Exception("Cannot find channel for service with org_id=%s service_id=%s group_name=%s and signer=%s" % (
                    self.args.org_id, self.args.service_id, self.args.group_name, self.ident.address))
            else:
                raise Exception("Cannot find channel for org_id=%s group_name=%s and signer=%s" % (
                    self.args.org_id, self.args.group_name, self.ident.address))
        if self.args.channel_id is None:
            if len(channels) > 1:
                channel_ids = [channel["channel_id"] for channel in channels]
                raise Exception(
                    "We have several channels: %s. You should use --channel-id to select one" % str(channel_ids))
            return channels[0]
        for channel in channels:
            if channel["channel_id"] == self.args.channel_id:
                return channel
        raise Exception(
            "Channel %i has not been opened or you are not the sender/signer of it" % self.args.channel_id)

    def channel_extend_and_add_funds_for_org(self):
        self._init_or_update_registered_org_if_needed()
        metadata = self._read_metadata_for_org(self.args.org_id)
        channel_id = self._smart_get_channel_for_org(metadata, "sender")["channelId"]
        self._channel_extend_add_funds_with_channel_id(channel_id)

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
        if not os.path.exists(sdir):
            raise Exception(
                "Service with org_id=%s is not initialized" % (org_id))
        return OrganizationMetadata.from_file(sdir.joinpath("organization_metadata.json"))

    def _convert_channel_dict_to_str(self, channel, filters=None):
        if filters is None:
            filters = []
        for key, value in channel.items():
            channel[key] = str(value)
        # converting to string not using " ".join() to always have the same order
        channel_as_str = ""
        channel_as_str += channel["channel_id"]
        channel_as_str += " " + channel["nonce"] if "nonce" in channel else ""
        channel_as_str += " " + channel["sender"] if "sender" not in filters else ""
        channel_as_str += " " + channel["signer"]
        channel_as_str += " " + channel["recipient"] if "recipient" not in filters else ""
        channel_as_str += " " + channel["group_id"] if "group_id" not in filters else ""
        channel_as_str += " " + channel["value"] if "value" in channel else ""
        channel_as_str += " " + channel["expiration"] if "expiration" in channel else ""
        return channel_as_str


    def _print_channels(self, channels, filters: list[str] = None):
        if filters is None:
            filters = []

        if self.args.only_id:
            self._printout("#channel_id")
            [self._printout(ch_id) for ch_id in channels]
            return

        titles = ["channel_id", "nonce", "sender", "signer", "recipient", "group_id", "value", "expiration"]
        for channel_filter in filters:
            titles.remove(channel_filter)

        if self.args.do_not_sync:
            titles.remove("nonce")
            titles.remove("value")
            titles.remove("expiration")
            self._printout("#" + " ".join(titles))
            for channel in channels:
                channel["group_id"] = base64.b64encode(channel["group_id"]).decode("ascii")
                self._printout(self._convert_channel_dict_to_str(channel, filters))
            return

        channels_ids = sorted(channels)
        self._printout("#" + " ".join(titles))
        for channel_id in channels_ids:
            channel = self._get_channel_state_from_blockchain(channel_id)
            channel["channel_id"] = channel_id
            channel["value"] = cogs2stragix(channel["value"])
            channel["group_id"] = base64.b64encode(channel["groupId"]).decode("ascii")
            self._printout(self._convert_channel_dict_to_str(channel, filters))

    def get_address_from_arg_or_ident(self, arg):
        if arg:
            return arg
        self.check_ident()
        return self.ident.address


    def print_channels_filter_sender(self):
        # we don't need to return other channel fields if we only need channel_id or if we'll sync channels state
        return_only_id = self.args.only_id or not self.args.do_not_sync
        address = self.get_address_from_arg_or_ident(self.args.sender)
        channels = self._get_filtered_channels(return_only_id=return_only_id, sender=address)
        self._printout("Channels for sender: %s" % address)
        self._print_channels(channels, ["sender"])

    def print_channels_filter_recipient(self):
        # we don't need to return other channel fields if we only need channel_id or if we'll sync channels state
        return_only_id = self.args.only_id or not self.args.do_not_sync
        address = self.get_address_from_arg_or_ident(self.args.recipient)
        channels = self._get_filtered_channels(return_only_id=return_only_id, recipient=address)
        self._printout("Channels for recipient: %s" % address)
        self._print_channels(channels, ["recipient"])

    def print_channels_filter_group(self):
        # we don't need to return other channel fields if we only need channel_id or if we'll sync channels state
        return_only_id = self.args.only_id or not self.args.do_not_sync
        metadata = self._get_organization_metadata_from_registry(self.args.org_id)
        recipient = metadata.get_payment_address_for_group(self.args.group_name)
        group_id = metadata.get_group_id_by_group_name(self.args.group_name)
        channels = self._get_filtered_channels(return_only_id=return_only_id, group_id=group_id)
        self._printout("Channels for group_id: %s and recipient: %s" % (group_id, recipient))
        self._print_channels(channels, ["group_id", "recipient"])

    def print_channels_filter_group_sender(self):
        # we don't need to return other channel fields if we only need channel_id or if we'll sync channels state
        return_only_id = self.args.only_id or not self.args.do_not_sync
        sender = self.get_address_from_arg_or_ident(self.args.sender)
        metadata = self._get_organization_metadata_from_registry(self.args.org_id)
        group_id = metadata.get_group_id_by_group_name(self.args.group_name)
        recipient = metadata.get_payment_address_for_group(self.args.group_name)
        channels = self._get_filtered_channels(return_only_id=return_only_id, sender=sender, group_id=group_id)
        self._printout("Channels for group_id: %s, sender: %s and recipient: %s" % (group_id, sender, recipient))
        self._print_channels(channels, ["sender", "group_id", "recipient"])

    def print_all_channels(self):
        # we don't need to return other channel fields if we only need channel_id or if we'll sync channels state
        return_only_id = self.args.only_id or not self.args.do_not_sync
        channels = self._get_filtered_channels(return_only_id=return_only_id)
        self._print_channels(channels)

    # Auxilary functions
    def print_block_number(self):
        self._printout(self.ident.w3.eth.block_number)

    def _get_service_registration(self):
        params = [type_converter("bytes32")(self.args.org_id), type_converter(
            "bytes32")(self.args.service_id)]
        response = self.call_contract_command(
            "Registry", "getServiceRegistrationById", params)
        if response[0] == False:
            raise Exception("Cannot find Service with id=%s in Organization with id=%s" % (
                self.args.service_id, self.args.org_id))
        return {"metadataURI": response[2]}

    def _get_service_metadata_from_registry(self):
        response = self._get_service_registration()
        storage_type, metadata_hash = bytesuri_to_hash(response["metadataURI"])
        if storage_type == "ipfs":
            service_metadata = get_from_ipfs_and_checkhash(self._get_ipfs_client(), metadata_hash)
        else:
            service_metadata = get_file_from_filecoin(metadata_hash)
        service_metadata = service_metadata.decode("utf-8")
        service_metadata = mpe_service_metadata_from_json(service_metadata)
        return service_metadata

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
        if os.path.exists(service_dir):
            shutil.rmtree(service_dir)

        os.makedirs(service_dir, mode=0o700)
        try:
            spec_dir = os.path.join(service_dir, "service_spec")
            os.makedirs(spec_dir, mode=0o700)
            service_api_source = metadata.get("service_api_source") or metadata.get("model_ipfs_hash")
            download_and_safe_extract_proto(service_api_source, spec_dir, self._get_ipfs_client())

            # compile .proto files
            if not compile_proto(Path(spec_dir), service_dir):
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
        if self.is_service_initialized():
            old_reg = self._read_service_info(
                self.args.org_id, self.args.service_id)

            # metadataURI will be in old_reg only for service which was initilized from registry (not from metadata)
            # we do nothing for services which were initilized from metadata
            if "metadataURI" not in old_reg:
                return

            service_registration = self._get_service_registration()
            # if metadataURI hasn't been changed we do nothing
            if not self.is_service_metadataURI_has_changed(service_registration):
                return
        else:
            service_registration = self._get_service_registration()

        service_metadata = self._get_service_metadata_from_registry()
        self._init_or_update_service_if_needed(
            service_metadata, service_registration)
