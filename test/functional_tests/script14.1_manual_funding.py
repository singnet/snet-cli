from snet_cli.sdk import Session, Client
from snet_cli.config import Config

session = Session(Config())

# we automatically open new channel!
# reserve funds for 1.5 call
session.reserve_funds("testo", "tests", amount_cogs = 15000, expiration = "+10days")
client = Client(session, "testo", "tests")

request = client.classes.ClassifyRequest(image_type = "jpg")
rez     = client.stub.classify(request)

# check that it works correctly with existed channel (reserve funds for 0.5 call)
session.reserve_funds("testo", "tests", amount_cogs = 5000, expiration = "+10days")

request = client.get_request_class("classify")(image_type = "jpg")
rez     = client.stub.classify(request)

# should be 0 now
assert client.unspent_amount() == 0

