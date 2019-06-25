# test itentities managment.

# This is first and second ganache identity
A0=0x592E3C0f3B038A0D673F19a18a773F993d4b2610
A1=0x3b2b3C2e2E7C93db335E69D827F3CC4bC2A2A2cB

assert_mpe_balance() {
	MPE_BALANCE=$(snet account balance --account $1 | grep MPE)
	test ${MPE_BALANCE##*:} = $2
}

# this should fail because snet-user should be in use now
snet identity delete snet-user && exit 1 || echo "fail as expected"

snet identity create key0 key --private-key 0xc71478a6d0fe44e763649de0a0deb5a080b788eefbbcf9c6f7aef0dd5dbd67e0 --network local

snet identity create rpc0 rpc --network local
snet identity rpc0

# switch to main net (rpc0 is bind to the local network!)
snet network mainnet
snet account balance && exit 1 || echo "fail as expected"
snet network local

snet account deposit 100 -y
assert_mpe_balance $A0 100

# A0 -> A1  42
snet account transfer $A1 42 -y
assert_mpe_balance $A1 42

snet identity create rpc1 rpc --network local --wallet-index 1
snet identity rpc1

# A1 -> A0  1
snet account transfer $A0 1 -y
assert_mpe_balance $A1 41

# A0 -> A1 2
snet account transfer $A1 2 --wallet-index 0 -y
assert_mpe_balance $A1 43

snet identity create mne0 mnemonic --network local --mnemonic "a b c d"
snet identity mne0
M0=$(snet account print)
M1=$(snet account print --wallet-index 1)

snet identity create mne1 mnemonic --wallet-index 1 --network local --mnemonic "a b c d"
snet identity mne1
M11=$(snet account print)

test $M1 = $M11

snet identity rpc0

# A0 -> M1 0.1
snet account transfer $M1 0.1 -y
assert_mpe_balance $M1 0.1

# A0 -> M1 0.2
snet identity key0
snet account transfer $M1 0.1 -y
assert_mpe_balance $M1 0.2

snet identity snet-user
snet identity delete rpc0
snet identity rpc0 && exit 1 || echo "fail as expected"

snet identity delete rpc1
snet identity delete mne0
snet identity delete mne1
