# safe conversion between agi(string) and cogs(int)
import decimal
AGI_TOKEN_DECIMALS = 8

def stragi2cogs(stragi):
    if (type(stragi) != str):
        raise Exception("Parameter should be string")

    # in case user write something stupid we set very big precision
    decimal.getcontext().prec = 1000
    cogs_decimal = decimal.Decimal(stragi) * 10**AGI_TOKEN_DECIMALS
    cogs_int     = int(cogs_decimal)
    if (cogs_int != cogs_decimal):
        raise Exception("AGI token has only %i decimals"%AGI_TOKEN_DECIMALS)    
    return cogs_int


def cogs2stragi(cogs_int):
    # presicison should be higer then INITIAL_SUPPLY + 1, we set it to 1000 be consistent with stragi2cogs
    decimal.getcontext().prec = 1000    
    agi_decimal = decimal.Decimal(cogs_int) / 10**AGI_TOKEN_DECIMALS
    return format(agi_decimal, 'f')
