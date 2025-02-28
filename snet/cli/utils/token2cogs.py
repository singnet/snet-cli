""" Safe conversion between token(string) and cogs(int) """
import decimal

TOKEN_DECIMALS = 18


def strtoken2cogs(str_token):
    if type(str_token) != str:
        raise Exception("Parameter should be string")

    # in case user write something stupid we set very big precision
    decimal.getcontext().prec = 1000
    cogs_decimal = decimal.Decimal(str_token) * 10 ** TOKEN_DECIMALS
    cogs_int = int(cogs_decimal)
    if cogs_int != cogs_decimal:
        raise Exception("ASI(FET) token has only %i decimals" % TOKEN_DECIMALS)
    return cogs_int


def cogs2strtoken(cogs_int):
    # presicison should be higer then INITIAL_SUPPLY + 1, we set it to 1000 be consistent with strtoken2cogs
    decimal.getcontext().prec = 1000
    token_decimal = decimal.Decimal(cogs_int) / 10 ** TOKEN_DECIMALS
    return format(token_decimal, 'f')
