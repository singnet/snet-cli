from snet_cli.utils import get_contract_def

# We try to get config address from the differnt sources.
# The order of priorioty is following:
# - command line argument (at)
# - command line argument (<contract_name>_at)
# - current session configuration (current_<contract_name>_at)
# - networks/*json
def get_contract_address(cmd, contract_name, error_message = None):

    # try to get from command line argument at or contractname_at
    a = "at"
    if (hasattr(cmd.args, a) and getattr(cmd.args, a)):
        return cmd.w3.toChecksumAddress( getattr(cmd.args, a) )

    # try to get from command line argument contractname_at
    a = "%s_at"%contract_name.lower()
    if (hasattr(cmd.args, a) and getattr(cmd.args, a)):
        return cmd.w3.toChecksumAddress( getattr(cmd.args, a) )


    # try to get from current session configuration
    rez = cmd.config.get_session_field("current_%s_at"%(contract_name.lower()), exception_if_not_found = False)
    if rez: return cmd.w3.toChecksumAddress(rez)

    error_message = error_message or "Fail to read %s address from \"networks\", you should specify address by yourself via --%s parameter"%(contract_name, contract_name.lower())
    chain_id = cmd.w3.version.network # this will raise exception if endpoint is invalid
    # try to take address from networks
    try :
        contract_def     = get_contract_def(contract_name)
        networks         = contract_def["networks"]
        contract_address = networks.get(chain_id, {}).get("address", None)
        if (not contract_address):
            raise Exception()
        contract_address = cmd.w3.toChecksumAddress(contract_address)
    except:
        raise Exception(error_message)

    return contract_address

def get_registry_address(cmd):
    return get_contract_address(cmd, "Registry")

def get_mpe_address(cmd):
    return get_contract_address(cmd, "MultiPartyEscrow")

def get_snt_address(cmd):
    return get_contract_address(cmd, "SingularityNetToken")



# we try to get field_name from diffent sources:
# The order of priorioty is following:
# - command line argument (--<field_name>)
# - current session configuration (default_<filed_name>)
def get_field_from_args_or_session(config, args, field_name):
    rez = getattr(args, field_name, None) or config.get_session_field("default_%s"%field_name, exception_if_not_found=False)
    if (not rez):
        raise Exception("Fail to get default_%s from config, should specify %s via --%s parameter"%(field_name, field_name, field_name.replace("_","-")))
    return rez

def get_wallet_index(config, args):
    return get_field_from_args_or_session(config, args, "wallet_index")

def get_gas_price(config, args):
    return int(get_field_from_args_or_session(config, args, "gas_price"))
