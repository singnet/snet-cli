from snet_cli.sdk import Session, Client, AutoFundingFundingStrategy
from snet_cli.config import Config

session = Session(Config())

# automatically refund for 2 calls
client = Client(session, "testo", "tests", AutoFundingFundingStrategy(amount_cogs = 20000, expiration = "+10days"))

for i in range(6):
    print("run", i)
    request = client.classes.ClassifyRequest(image_type = "jpg")
    rez     = client.stub.classify(request)

assert client.unspent_amount() == 0
