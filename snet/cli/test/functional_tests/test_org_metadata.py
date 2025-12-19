import os
from func_tests import BaseTest, execute, ADDR
import unittest


class TestOrgMetadata(BaseTest):
    def setUp(self):
        super().setUp()
        self.success_msg = "Organization metadata is valid and ready to publish."
        self.name = "test_org"
        self.org_id = "test_org_id"
        self.org_type = "individual"
        self.org_description = "--description"
        self.org_short_description = "--short-description"
        self.org_url = "--url"
        self.group_name = "default_group"
        self.endpoint = "https://node1.naint.tech:62400"

    def test_metadata_init(self):
        execute(["organization", "metadata-init", self.name, self.org_id, self.org_type], self.parser, self.conf)
        execute(["organization", "metadata-add-description", self.org_description, "DESCRIPTION", self.org_short_description, "SHORT_DESCRIPTION", self.org_url, "https://URL"],
                self.parser,
                self.conf)
        execute(["organization", "add-group", self.group_name, ADDR, self.endpoint], self.parser, self.conf)
        result = execute(["organization", "validate-metadata"], self.parser, self.conf)
        assert self.success_msg in result

    def tearDown(self):
        os.remove(f"./organization_metadata.json")


if __name__ == "__main__":
    unittest.main()
