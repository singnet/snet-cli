from snet_cli.sdk import Session, Client, AutoFundingFundingStrategy
from snet_cli.config import Config

session = Session(Config())

# automatically refund for 2 calls
client = Client(session, "testo", "tests2", AutoFundingFundingStrategy(amount_cogs = 20000, expiration = "+10days"))

for i in range(6):
    print("run", i)
    request = client.classes.ClassifyRequest(image_type = "jpg")
    rez     = client.stub.classify(request)

assert client.unspent_amount() == 0

# make expiration_threshold_blocks (=11 days) more then 10 days, so we test channel extension (in case of 0 fund in it)
client = Client(session, "testo", "tests2", AutoFundingFundingStrategy(amount_cogs = 20000, expiration = "+20days", expiration_threshold_blocks = 63360))

request = client.classes.ClassifyRequest(image_type = "jpg")
rez     = client.stub.classify(request)

# we should have funds for one call
assert client.unspent_amount() == 10000

# make expiration_threshold_blocks (=21 days) more then 20 days, so we test channel extension (in case of some fund in it)
client = Client(session, "testo", "tests2", AutoFundingFundingStrategy(amount_cogs = 20000, expiration = "+30days", expiration_threshold_blocks = 120960))

request = client.classes.ClassifyRequest(image_type = "jpg")
rez     = client.stub.classify(request)

assert client.unspent_amount() == 0

