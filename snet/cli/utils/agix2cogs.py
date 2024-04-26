""" Safe conversion between agix(string) and cogs(int) """
import decimal

AGIX_TOKEN_DECIMALS = 8


def stragix2cogs(stragix):
    if type(stragix) != str:
        raise Exception("Parameter should be string")

    # in case user write something stupid we set very big precision
    decimal.getcontext().prec = 1000
    cogs_decimal = decimal.Decimal(stragix) * 10 ** AGIX_TOKEN_DECIMALS
    cogs_int = int(cogs_decimal)
    if cogs_int != cogs_decimal:
        raise Exception("AGIX token has only %i decimals" % AGIX_TOKEN_DECIMALS)
    return cogs_int


def cogs2stragix(cogs_int):
    # presicison should be higer then INITIAL_SUPPLY + 1, we set it to 1000 be consistent with stragix2cogs
    decimal.getcontext().prec = 1000
    agix_decimal = decimal.Decimal(cogs_int) / 10 ** AGIX_TOKEN_DECIMALS
    return format(agix_decimal, 'f')
