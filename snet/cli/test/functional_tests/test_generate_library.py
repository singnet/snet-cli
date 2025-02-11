import unittest
import os
from func_tests import BaseTest, execute
import shutil


class TestGenerateLibrary(BaseTest):
    def setUp(self):
        super().setUp()
        self.path = './temp_files'
        self.org_id = '26072b8b6a0e448180f8c0e702ab6d2f'
        self.service_id = 'Exampleservice'

    def test_generate(self):
        execute(["sdk", "generate-client-library", self.org_id, self.service_id, self.path], self.parser, self.conf)
        assert os.path.exists(f'{self.path}/{self.org_id}/{self.service_id}/python/')

    def tearDown(self):
        shutil.rmtree(self.path)


if __name__ == "__main__":
    unittest.main()
