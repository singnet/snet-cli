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
from snet_cli.utils_proto4sdk import import_protobuf_from_dir_for_given_service_name
from snet_cli.utils import open_grpc_channel


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

    # amount_cogs MUST be a named argument in order to prevent errors
    def reserve_funds(self, org_id, service_id, *, amount_cogs, expiration, group_name = None):
        # TODO remove two transaction... It is a hack...
        params      = DefaultAttributeObject(org_id = org_id, service_id = service_id, amount = amount_cogs, expiration = expiration,
                                             open_new_anyway = False, from_block = 0, yes = True)
        channel_command = MPEChannelCommand(self.config, params, self.out_f, self.err_f, w3 = self.w3, ident = self.ident)

        # Open new channel if needed
        if (channel_command.open_init_channel_from_registry() is not None):
            self._printerr("# new channel with %i cogs have been opened for %s %s"%(amount_cogs, org_id, service_id))
            return
        channel_command.channel_extend_and_add_funds_for_service()
        self._printerr("# we've added %i cogs for %s %s"%(amount_cogs, org_id, service_id))

class _ClientCallDetails(
               collections.namedtuple( '_ClientCallDetails',
               ('method', 'timeout', 'metadata', 'credentials')),
               grpc.ClientCallDetails):
    pass

class BasicFundingStrategy:
    def init_for_client(self, client):
        pass
    def fund_and_extend_if_needed(self, service_state):
        pass


class Client(MPEClientCommand):
    def __init__(self, session, org_id, service_id, funding_strategy = BasicFundingStrategy(), grpc_service_name = None, skip_update_check = False, group_name = None):
        args = DefaultAttributeObject(org_id = org_id, service_id = service_id, group_name = group_name, yes = True)
        super(Client, self).__init__(session.config, args, session.out_f, session.err_f, w3 = session.w3, ident = session.ident)
        self.session = session

        if (not skip_update_check):
            self._init_or_update_registered_service_if_needed()

        funding_strategy.init_for_client(self)
        self.funding_strategy = funding_strategy

        self.service_metadata   = self._read_metadata_for_service(self.args.org_id, self.args.service_id)
        self.endpoint           = self._get_endpoint_from_metadata_or_args(self.service_metadata)
        self._pure_grpc_channel = open_grpc_channel(self.endpoint)


        spec_dir = self.get_service_spec_dir(self.args.org_id, self.args.service_id)
        self.stub_class, self.methods_iodict, self.protobuf_file_prefix = import_protobuf_from_dir_for_given_service_name(spec_dir, grpc_service_name)

        self.channel  = self._smart_get_initialized_channel_for_service(self.service_metadata, filter_by = "signer")
        self.channel_id = self.channel["channelId"]

        if self.service_metadata["encoding"] == "json":
            for _, (_, response_class) in self.methods_iodict.items():
                switch_to_json_payload_encoding(call_fn, response_class)

        self.grpc_channel = grpc.intercept_channel(self._pure_grpc_channel, generic_client_interceptor.create(self.intercept_call))
        self.stub = self.stub_class(self.grpc_channel)

        self.classes = __import__("%s_pb2"%self.protobuf_file_prefix)

    def get_request_class(self, method):
        return self.methods_iodict[method][0]

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

        self.funding_strategy.fund_and_extend_if_needed(server_state)

        price         = self._get_price_from_metadata(self.service_metadata)
        metadata      = self._create_call_metadata(channel_id, server_state["current_nonce"], server_state["current_signed_amount"] + price)
        return metadata


class AutoFundingFundingStrategy:
    # force amount_cogs and expiration be named parameters (in order to be sure that amount are passed in cogs!)
    # expiration_threshold_blocks is default to 8 days (1 day more then default payment_expiration_threshold for services)
    def __init__(self, *, amount_cogs, expiration, expiration_threshold_blocks = 46080):
        self.funding_amount_cogs          = amount_cogs
        self.expiration                   = expiration
        self.expiration_threshold_blocks  = expiration_threshold_blocks

    def init_for_client(self, client):
        # open new channel if needed
        client.session._open_channel_if_not_exists(client.args.org_id, client.args.service_id, self.funding_amount_cogs, self.expiration, client.args.group_name)
        self.client = client


    def fund_and_extend_if_needed(self, service_state):
        client     = self.client
        channel_id = client.channel_id

        # Do we need extend our channel?
        is_extend = False
        current_block = client.ident.w3.eth.blockNumber
        if (client.channel["expiration"] - current_block < self.expiration_threshold_blocks):
            client.channel = client._get_channel_state_from_blockchain_update_cache(channel_id)
            if (client.channel["expiration"] - current_block < self.expiration_threshold_blocks):
                is_extend = True

        # Do we need to fund our channel?
        price          = client._get_price_from_metadata(client.service_metadata)
        server_state   = client._get_channel_state_from_server(client._pure_grpc_channel, channel_id)
        unspent_amount = client._calculate_unspent_amount(client.channel, server_state)
        is_fund = False
        if (unspent_amount is not None and unspent_amount < price):
            # update channel state from blockchain
            client.channel = client._get_channel_state_from_blockchain_update_cache(channel_id)
            unspent_amount = client._calculate_unspent_amount(client.channel, server_state)
            if (unspent_amount is not None and unspent_amount < price):
                is_fund = True

        expiration = client._expiration_str_to_blocks(self.expiration, client.ident.w3.eth.blockNumber)

        if (expiration - current_block < self.expiration_threshold_blocks):
            raise Exception("Expiration=%s is effectivly smaller then your expiration_threshold_blocks=%i"%(self.expiration, self.expiration_threshold_blocks))

        if (is_extend and not is_fund):
            client.transact_contract_command("MultiPartyEscrow", "channelExtend", [channel_id, expiration])

        if (is_fund):
            if (client.channel["expiration"] < expiration):
                client.transact_contract_command("MultiPartyEscrow", "channelExtendAndAddFunds", [channel_id, expiration, self.funding_amount_cogs])
            else:
                client.transact_contract_command("MultiPartyEscrow", "channelAddFunds", [channel_id, self.funding_amount_cogs])
