from snet_cli.commands import BlockchainCommand
from snet_cli.mpe_account_command import MPEAccountCommand
from snet_cli.mpe_channel_command import MPEChannelCommand
from snet_cli.mpe_client_command import MPEClientCommand
from snet_cli.utils_agi2cogs import stragi2cogs
import sys
from snet_cli.utils import DefaultAttributeObject
import snet_cli.generic_client_interceptor as generic_client_interceptor
import collections
import grpc

class Session(BlockchainCommand):
    def __init__(self, config, out_f=sys.stdout, err_f=sys.stderr):
        super(Session, self).__init__(config, {}, out_f, err_f)

    def mpe_deposit(self, cogs):
        account_command = MPEAccountCommand(self.config, DefaultAttributeObject(amount = cogs, yes = True),
                                            self.out_f, self.err_f, w3 = self.w3, ident = self.ident)
        account_command.deposit_to_mpe()

    def mpe_withdraw(self, cogs):
        account_command = MPEAccountCommand(self.config, DefaultAttributeObject(amount=cogs, yes = True),
                                            self.out_f, self.err_f, w3 = self.w3, ident = self.ident)
        account_command.withdraw_from_mpe()

    def _open_channel_if_not_exists(self, org_id, service_id, amount_cogs, expiration,  group_name = None):

        params      = DefaultAttributeObject(org_id = org_id, service_id = service_id, amount = amount_cogs, expiration = expiration,
                                             open_new_anyway = False, from_block = 0, group_name = group_name, yes = True)
        channel_command = MPEChannelCommand(self.config, params, self.out_f, self.err_f, w3 = self.w3, ident = self.ident)

        channel_command.open_init_channel_from_registry()

    def channel_extend_add(self, org_id, service_id, amount_cogs, expiration, group_name = None):
        params      = DefaultAttributeObject(org_id = org_id, service_id = service_id, amount = amount_cogs, expiration = expiration,
                                             open_new_anyway = False, from_block = 0)
        channel_command = MPEChannelCommand(self.config, params, self.out_f, self.err_f, w3 = self.w3, ident = self.ident)
        channel_command.open_init_channel_from_registry()

class _ClientCallDetails(
               collections.namedtuple( '_ClientCallDetails',
               ('method', 'timeout', 'metadata', 'credentials')),
               grpc.ClientCallDetails):
    pass


class BasicClient(MPEClientCommand):
    def __init__(self, session, org_id, service_id, method, skip_update_check = False, group_name = None):
        args = DefaultAttributeObject(org_id = org_id, service_id = service_id, method = method, group_name = group_name, yes = True)
        super(BasicClient, self).__init__(session.config, args, session.out_f, session.err_f, w3 = session.w3, ident = session.ident)

        if (not skip_update_check):
            self._init_or_update_registered_service_if_needed()

        self.service_metadata   = self._read_metadata_for_service(self.args.org_id, self.args.service_id)
        self.endpoint           = self._get_endpoint_from_metadata_or_args(self.service_metadata)
        self._pure_grpc_channel = self._open_grpc_channel(self.endpoint)
        self.stub_class, self.request_class, self.response_class = self._import_protobuf_for_service()
        self.channel  = self._smart_get_initialized_channel_for_service(self.service_metadata, filter_by = "signer")
        self.channel_id = self.channel["channelId"]

        if self.service_metadata["encoding"] == "json":
            switch_to_json_payload_encoding(call_fn, response_class)

        self.grpc_channel = grpc.intercept_channel(self._pure_grpc_channel, generic_client_interceptor.create(self.intercept_call))

        self.stub = self.stub_class(self.grpc_channel)

    def unspent_amount(self):
        _,_,unspent_amount = self._get_channel_state_statelessly(self._pure_grpc_channel, self.channel_id)
        return unspent_amount

    def intercept_call(self, client_call_details, request_iterator, request_streaming, response_streaming):
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        metadata.extend(self.get_call_metadata())
        client_call_details = _ClientCallDetails(client_call_details.method, client_call_details.timeout, metadata,
                                                 client_call_details.credentials)
        return client_call_details, request_iterator, None

    def get_call_metadata(self):
        channel_id    = self.channel_id
        server_state  = self._get_channel_state_from_server(self._pure_grpc_channel, channel_id)
        price         = self._get_price_from_metadata(self.service_metadata)
        metadata      = self._create_call_metadata(channel_id, server_state["current_nonce"], server_state["current_signed_amount"] + price)
        return metadata

class AutoFundingClient(BasicClient):
    def __init__(self, session, org_id, service_id, method, amount_cogs, expiration, expiration_margin = 5760, group_name = None):

        self.expiration             = expiration
        self.expiration_margin      = expiration_margin
        self.funding_amount_cogs    = amount_cogs

        # open new channel if needed
        session._open_channel_if_not_exists(org_id, service_id, amount_cogs, expiration, group_name)

        # we skip_update_check because we've already checked for update in open_channel_if_not_exists
        super(AutoFundingClient, self).__init__(session, org_id, service_id, method, skip_update_check = True, group_name = group_name)


    def _fund_and_extend_if_needed(self, service_state):
        channel_id = self.channel_id

        # Do we need extend our channel?
        is_extend = False
        current_block = self.ident.w3.eth.blockNumber
        if (self.channel["expiration"] - current_block < self.expiration_margin):
            self.channel = self._get_channel_state_from_blockchain_update_cache(channel_id)
            if (self.channel["expiration"] - current_block < self.expiration_margin):
                is_extend = True

        # Do we need to fund our channel
        price          = self._get_price_from_metadata(self.service_metadata)
        server_state   = self._get_channel_state_from_server(self._pure_grpc_channel, self.channel_id)
        unspent_amount = self._calculate_unspent_amount(self.channel, server_state)
        is_fund = False
        if (unspent_amount is not None and unspent_amount < price):
            # update channel state from blockchain
            self.channel = self._get_channel_state_from_blockchain_update_cache(channel_id)
            unspent_amount = self._calculate_unspent_amount(self.channel, server_state)
            if (unspent_amount is not None and unspent_amount < price):
                is_fund = True

        expiration = self._expiration_str_to_blocks(self.expiration)

        if (is_extend and not is_fund):
            self.transact_contract_command("MultiPartyEscrow", "channelExtend", [channel_id, expiration])

        if (is_fund):
            if (self.channel["expiration"] < expiration):
                self.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [channel_id, expiration, self.funding_amount_cogs])
            else:
                self.transact_contract_command("MultiPartyEscrow", "channelAddFunds", [channel_id, self.funding_amount_cogs])

    def get_call_metadata(self):
        channel_id    = self.channel_id
        server_state  = self._get_channel_state_from_server(self._pure_grpc_channel, channel_id)
        self._fund_and_extend_if_needed(server_state)
        price         = self._get_price_from_metadata(self.service_metadata)
        metadata      = self._create_call_metadata(channel_id, server_state["current_nonce"], server_state["current_signed_amount"] + price)
        return metadata
