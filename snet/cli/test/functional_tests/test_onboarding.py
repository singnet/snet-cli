import os
from func_tests import BaseTest, execute
import json
import unittest


class TestOrganization(BaseTest):
    def setUp(self):
        super().setUp()
        self.org_id = "singularitynet"
        self.correct_msg = f"List of {self.org_id}'s Services:"

    def test_list_of_services(self):
        result = execute(["organization", "list-services", self.org_id], self.parser, self.conf)
        assert self.correct_msg in result

    def test_org_info(self):
        result = execute(["organization", "info", self.org_id], self.parser, self.conf)
        assert "Organization Name" in result


""" temporarily closed so as not to clog up the logs
class TestOnboardingOrgAndServ(BaseTest):
    def setUp(self):
        super().setUp()
        self.identity_name = "identity_name"
        self.proto = "./"
        self.org_name = "auto_test"
        self.org_id = "auto_test"
        self.org_type = "individual"
        self.description = "DESCRIPTION"
        self.short_description = "SHORT DESCRIPTION"
        self.url = "https://URL.com"
        self.group_name = "default_group"
        self.endpoint = "https://node1.naint.tech:62400"
        self.password = "12345"
        self.service_id = "auto_test_service"
        self.new_description = "NEW DESCRIPTION"
        self.free_calls = "100"
        self.contributor = "Stasy"
        self.contributor_mail = "stasy@hotmail.com"
        self.tags = "new", "text2text", "t2t", "punctuality"
        self.tags2 = "update-add-tag"
        self.hero_image = "./img.jpg"
        self.contact = "author"
        self.email = "author@hotmail.com"
        self.phone = "+1234567890"

    def test_0_preparation(self):
        identity_list = execute(["identity", "list"], self.parser, self.conf)
        if self.identity_name not in identity_list:
            execute(["identity", "create", self.identity_name, "key", "--private-key", PRIVATE_KEY, "-de"], self.parser, self.conf)
        execute(["network", "sepolia"], self.parser, self.conf)
        proto_file = open("ExampleService.proto", "w+")
        proto_file.write("syntax = "proto3";

package example_service;

message Numbers {
    float a = 1;
    float b = 2;
}

message Result {
    float value = 1;
}

service Calculator {
    rpc add(Numbers) returns (Result) {}
    rpc sub(Numbers) returns (Result) {}
    rpc mul(Numbers) returns (Result) {}
    rpc div(Numbers) returns (Result) {}
}")
        proto_file.close()
        result = execute(["session"], self.parser, self.conf)
        hero_image = open("img.jpg", "w+")
        hero_image.close()
        assert "network: sepolia" in result

    def test_1_metadata_init(self):
        execute(["organization", "metadata-init", self.org_id, self.org_name, self.org_type], self.parser, self.conf)
        execute(["organization", "metadata-add-description", "--description", self.description, "--short-description", self.short_description, "--url", self.url],
                self.parser,
                self.conf)
        execute(["organization", "add-group", self.group_name, ADDR, self.endpoint], self.parser, self.conf)
        execute(["service", "metadata-init", self.proto, self.service_id], self.parser, self.conf)
        assert os.path.exists("./organization_metadata.json"), "File organization_metadata.json was not created!"

    def test_2_create_organization(self):
        result = execute(["organization", "create", self.org_id, "-y"], self.parser, self.conf)
        assert "event: OrganizationCreated" in result

    def test_31_create_service(self):
        result = execute(["service", "publish", self.org_id, self.service_id, "-y"], self.parser, self.conf)
        assert "event: ServiceCreated" in result

    def test_32_publish_in_ipfs(self):
        result = execute(["service", "publish-in-ipfs", "-y"], self.parser, self.conf)
        assert len(result) > 45

    def test_33_publish_in_filecoin(self):
        execute(["set", "filecoin_api_key", "8dcbe8a5.0e1595c6c556430dad42ef13abc00e2f"], self.parser, self.conf)
        result = execute(["service", "publish-in-filecoin", "-y"], self.parser, self.conf)
        print(result)
        assert "Ok" in result

    def test_41_list(self):
        result = execute(["organization", "list"], self.parser, self.conf)
        assert self.org_id in result

    def test_42_list_org_names(self):
        result = execute(["organization", "list-org-names"], self.parser, self.conf)
        assert self.org_name in result

    def test_43_list_my(self):
        result = execute(["organization", "list-my"], self.parser, self.conf)
        assert self.org_id in result

    def test_44_list_services(self):
        result = execute(["organization", "list-services", self.org_id], self.parser, self.conf)
        assert self.service_id in result


    def test_5_change_members(self):
        result_add = execute(["organization", "add-members", self.org_id, ADDR, "-y"], self.parser, self.conf)
        result_rem = execute(["organization", "rem-members", self.org_id, ADDR, "-y"], self.parser, self.conf)
        # result_change_owner = execute(["organization", "change-owner", self.org_id, ADDR], self.parser, self.conf)
        assert "event: OrganizationModified" in result_rem

    def test_61_change_org_metadata(self):
        execute(["organization", "metadata-add-assets", self.hero_image, "hero_image"], self.parser, self.conf)
        execute(["organization", "metadata-remove-assets", "hero_image"], self.parser, self.conf)
        execute(["organization", "metadata-remove-all-assets"], self.parser, self.conf)
        execute(["organization", "metadata-add-contact", self.contact, "--email", self.email, "--phone", self.phone], self.parser, self.conf)
        execute(["organization", "metadata-remove-contacts", self.contact], self.parser, self.conf)
        execute(["organization", "metadata-remove-all-contacts"], self.parser, self.conf)
        execute(["organization", "metadata-add-description", "--description", self.new_description], self.parser, self.conf)
        execute(["organization", "update-metadata", self.org_id, "-y"], self.parser, self.conf)
        result = execute(["organization", "print-metadata", self.org_id], self.parser, self.conf)
        assert self.new_description in result

    @patch("builtins.input", side_effect=["1", "2"])
    def test_62_change_service_metadata(self, mock_input):
        execute(["service", "metadata-remove-group", self.group_name], self.parser, self.conf)
        execute(["service", "metadata-add-group", self.group_name], self.parser, self.conf)
        execute(["organization", "update-group", self.group_name], self.parser, self.conf)
        execute(["service", "metadata-add-daemon-addresses", self.group_name, ADDR], self.parser, self.conf)
        execute(["service", "metadata-remove-all-daemon-addresses", self.group_name], self.parser, self.conf)
        execute(["service", "metadata-update-daemon-addresses", self.group_name, ADDR], self.parser, self.conf)
        execute(["service", "metadata-add-endpoints", self.group_name, self.endpoint], self.parser, self.conf)
        execute(["service", "metadata-remove-all-endpoints", self.group_name], self.parser, self.conf)
        execute(["service", "metadata-add-endpoints", self.group_name, self.endpoint], self.parser, self.conf)
        execute(["service", "metadata-set-free-calls", self.group_name, self.free_calls], self.parser, self.conf)
        execute(["service", "metadata-set-freecall-signer-address", self.group_name, ADDR], self.parser, self.conf)
        execute(["service", "metadata-add-description", "--description", self.new_description, "--short-description", self.short_description, "--url", self.url],
                self.parser,
                self.conf)
        execute(["service", "metadata-add-contributor", self.contributor, self.contributor_mail], self.parser, self.conf)
        execute(["service", "metadata-remove-contributor", self.contributor_mail], self.parser, self.conf)
        execute(["service", "metadata-add-contributor", self.contributor, self.contributor_mail], self.parser, self.conf)
        execute(["service", "metadata-add-assets", self.hero_image, "hero_image"], self.parser, self.conf)
        execute(["service", "metadata-remove-assets", "hero_image"], self.parser, self.conf)
        execute(["service", "metadata-remove-all-assets"], self.parser, self.conf)
        execute(["service", "metadata-add-media", self.hero_image], self.parser, self.conf)
        execute(["service", "metadata-remove-media", "1"], self.parser, self.conf)
        execute(["service", "metadata-remove-all-media"], self.parser, self.conf)
        execute(["service", "metadata-add-media", self.hero_image], self.parser, self.conf)
        execute(["service", "metadata-add-media", self.hero_image], self.parser, self.conf)
        execute(["service", "metadata-swap-media-order", "1", "2"], self.parser, self.conf)
        execute(["service", "metadata-change-media-order"], self.parser, self.conf)
        execute(["service", "update-metadata", self.org_id, self.service_id, "-y"], self.parser, self.conf)
        result = execute(["service", "print-metadata", self.org_id, self.service_id], self.parser, self.conf)
        print(execute(["service", "print-metadata", self.org_id, self.service_id], self.parser, self.conf))
        print(execute(["service", "print-service-status", self.org_id, self.service_id], self.parser, self.conf))
        assert self.contributor in result

    TODO: New logic for adding tags
    def test_63_tags(self):
        execute(["service", "metadata-add-tags", self.tags], self.parser, self.conf)
        execute(["service", "update-metadata", self.org_id, self.service_id, "-y"], self.parser, self.conf)
        execute(["service", "metadata-remove-tags", self.tags], self.parser, self.conf)
        execute(["service", "update-add-tags", self.org_id, self.service_id, self.tags2, "-y"], self.parser, self.conf)
        execute(["service", "update-remove-tags", self.org_id, self.service_id, self.tags2, "-y"], self.parser, self.conf)
        print(execute(["service", "print-tags", self.org_id, self.service_id], self.parser, self.conf))
        result = execute(["service", "print-tags", self.org_id, self.service_id], self.parser, self.conf)
        assert self.tags in result


    def test_64_get_api_metadata(self):
        os.remove(f"./ExampleService.proto")
        execute(["service", "get-api-metadata", "./"], self.parser, self.conf)
        assert os.path.exists(f"./ExampleService.proto")

    def test_65_metadata_set_api(self):
        res = execute(["service", "metadata-set-api", "./", "--storage", "ipfs"], self.parser, self.conf)
        print(res)
        with open("service_metadata.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)
        assert metadata["service_api_source"].startswith("ipfs://")

    @patch("builtins.input", side_effect=["auto_test", "1", "ipfs", "./", "y", "default_group", "1", ADDR, ADDR, "y", "150", ADDR, "n", "google.com", "long description", "short", "Stasy", "stasy@hotmail.com", "n", "y", "service_metadata"])
    def test_66_metadata_init_utility(self, mock_input):
        os.remove(f"./service_metadata.json")
        execute(["service", "metadata-init-utility"], self.parser, self.conf)
        assert os.path.exists(f"./service_metadata.json")

    def test_7_delete_service(self):
        result = execute(["service", "delete", self.org_id, self.service_id, "-y"], self.parser, self.conf)
        os.remove(f"./service_metadata.json")
        assert "event: ServiceDeleted" in result

    def test_8_delete_organization(self):
        result = execute(["organization", "delete", self.org_id, "-y"], self.parser, self.conf)
        os.remove(f"./organization_metadata.json")
        os.remove(f"img.jpg")
        assert "event: OrganizationDeleted" in result
"""


if __name__ == "__main__":
    unittest.main()