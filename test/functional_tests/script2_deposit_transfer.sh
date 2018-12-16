# test deposit and transfer functions in snet client

# initial balance should be 0
MPE_BALANCE=$(snet account balance|grep MPE)
test ${MPE_BALANCE##*:} = "0"

snet account deposit 12345.678 -y -q

MPE_BALANCE=$(snet account balance|grep MPE)
test ${MPE_BALANCE##*:} = "12345.678"

snet account transfer 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18 42.314 -y -q

MPE_BALANCE=$(snet account balance --account 0x0067b427E299Eb2A4CBafc0B04C723F77c6d8a18|grep MPE)
test ${MPE_BALANCE##*:} = "42.314"


MPE_BALANCE=$(snet account balance|grep MPE)
test ${MPE_BALANCE##*:} = "12303.364"


snet account withdraw 1.42 -y -q
MPE_BALANCE=$(snet account balance|grep MPE)
test ${MPE_BALANCE##*:} = "12301.944"
