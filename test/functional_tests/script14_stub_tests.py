from snet_cli.call_stub_generator import call_stub_generator

stub = call_stub_generator("testo", "tests", "classify")

rez = stub.call_server_statelessly_with_params({})
print(rez)
