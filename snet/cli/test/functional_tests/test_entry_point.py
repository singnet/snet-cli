import unittest
import os


class TestEntryPoint(unittest.TestCase):
    def test_help(self):
        exit_status = os.system('snet --help')
        self.assertEqual(0, exit_status)

    def test_identity(self):
        exit_status = os.system('snet identity list')
        self.assertEqual(0, exit_status)

    def test_account(self):
        exit_status = os.system('snet account -h')
        self.assertEqual(0, exit_status)

    def test_channel(self):
        exit_status = os.system('snet channel -h')
        self.assertEqual(0, exit_status)

    def test_client(self):
        exit_status = os.system('snet client -h')
        self.assertEqual(0, exit_status)

    def test_contract(self):
        exit_status = os.system('snet contract -h')
        self.assertEqual(0, exit_status)

    def test_network(self):
        exit_status = os.system('snet network list')
        self.assertEqual(0, exit_status)

    def test_organization(self):
        exit_status = os.system('snet organization -h')
        self.assertEqual(0, exit_status)

    def test_sdk(self):
        exit_status = os.system('snet sdk -h')
        self.assertEqual(0, exit_status)

    def test_service(self):
        exit_status = os.system('snet service -h')
        self.assertEqual(0, exit_status)

    def test_session(self):
        exit_status = os.system('snet session -h')
        self.assertEqual(0, exit_status)

    def test_set(self):
        exit_status = os.system('snet set -h')
        self.assertEqual(0, exit_status)

    def test_treasurer(self):
        exit_status = os.system('snet treasurer -h')
        self.assertEqual(0, exit_status)

    def test_unset(self):
        exit_status = os.system('snet unset -h')
        self.assertEqual(0, exit_status)

    def test_version(self):
        exit_status = os.system('snet version')
        self.assertEqual(0, exit_status)


if __name__ == '__main__':
    cli_tests = unittest.TestLoader().loadTestsFromTestCase(TestEntryPoint)
    functional_tests = unittest.TestLoader().discover("./snet/cli/test/functional_tests", pattern="test_*.py")
    all_tests = unittest.TestSuite([cli_tests, functional_tests])
    unittest.TextTestRunner().run(all_tests)
