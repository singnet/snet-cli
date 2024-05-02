import unittest
import os


class TestEntryPoint(unittest.TestCase):
    def test_help(self):
        exit_status = os.system('snet --help')
        assert exit_status == 0

    def test_identity(self):
        exit_status = os.system('snet identity list')
        assert exit_status == 0

    def test_account(self):
        exit_status = os.system('snet account -h')
        assert exit_status == 0

    def test_channel(self):
        exit_status = os.system('snet channel -h')
        assert exit_status == 0

    def test_client(self):
        exit_status = os.system('snet client -h')
        assert exit_status == 0

    def test_contract(self):
        exit_status = os.system('snet contract -h')
        assert exit_status == 0

    def test_network(self):
        exit_status = os.system('snet network list')
        assert exit_status == 0

    def test_organization(self):
        exit_status = os.system('snet organization -h')
        assert exit_status == 0

    def test_sdk(self):
        exit_status = os.system('snet sdk -h')
        assert exit_status == 0

    def test_service(self):
        exit_status = os.system('snet service -h')
        assert exit_status == 0

    def test_session(self):
        exit_status = os.system('snet session -h')
        assert exit_status == 0

    def test_set(self):
        exit_status = os.system('snet set -h')
        assert exit_status == 0

    def test_treasurer(self):
        exit_status = os.system('snet treasurer -h')
        assert exit_status == 0

    def test_unset(self):
        exit_status = os.system('snet unset -h')
        assert exit_status == 0

    def test_version(self):
        exit_status = os.system('snet version')
        assert exit_status == 0


if __name__ == '__main__':
    unittest.main()

