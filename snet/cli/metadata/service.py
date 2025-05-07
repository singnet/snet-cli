"""
Functions for manipulating service metadata

Metadata format:
----------------------------------------------------
version          - used to track format changes (current version is 1)
display_name     - Display name of the service
encoding         - Service encoding (proto or json)
service_type     - Service type (grpc, jsonrpc or process)
service_description - Service description (arbitrary field)
payment_expiration_threshold - Service will reject payments with expiration less
                                than current_block + payment_expiration_threshold.
                               This field should be used by the client with caution.
                               Client should not accept arbitrary payment_expiration_threshold
service_api_source  - HASH with the storage type prefix to the .tar archive of protobuf service specification
mpe_address      - Address of MultiPartyEscrow contract.
                   Client should use it exclusively for cross-checking of mpe_address,
                        (because service can attack via mpe_address)
                   Daemon can use it directly if authenticity of metadata is confirmed
pricing {}      -  Pricing model
         Possible pricing models:
         1. Fixed price
             price_model   - "fixed_price"
             price_in_cogs -  unique fixed price in cogs for all method (1 ASI(FET) = 10^18 cogs)
             (other pricing models can be easily supported)
groups []       - group is the number of endpoints which shares same payment channel;
                  grouping strategy is defined by service provider;
                  for example service provider can use region name as group name
     group_name - unique name of the group (human readable)
     group_id   - unique id of the group (random 32 byte string in base64 encoding)
     payment_address - Ethereum address to recieve payments
endpoints[]     - address in the off-chain network to provide a service
     group_name
     endpoint   -  unique endpoint identifier (ip:port)

assets {}       -  asset type and its ipfs value/values
"""

import re
import json
import base64

from collections import defaultdict
from enum import Enum

from snet.cli.utils.utils import is_valid_endpoint


# Supported Asset types
class AssetType(Enum):
    HERO_IMAGE = "hero_image"
    IMAGES = "images"
    DOCUMENTATION = "documentation"
    TERMS_OF_USE = "terms_of_use"

    @staticmethod
    def is_single_value(asset_type):
        if asset_type == AssetType.HERO_IMAGE.value or asset_type == AssetType.DOCUMENTATION.value or asset_type == AssetType.TERMS_OF_USE.value:
            return True


# TODO: we should use some standard solution here
class MPEServiceMetadata:

    def __init__(self):
        self.m = {"version": 1,
                  "display_name": "",
                  "encoding": "proto",  # proto by default
                  "service_type": "grpc",  # grpc by default
                  # one week by default (15 sec block,  24*60*60*7/15)
                  "service_api_source": "",
                  "mpe_address": "",
                  "groups": [],
                  "assets": {},
                  "media": [],
                  "tags": []
                  }

    def set_simple_field(self, f, v):
        if f != "display_name" and f != "encoding" and f != "mpe_address" and f != "service_type" and \
                f != "payment_expiration_threshold" and f != "service_description" and f != "service_api_source":
            raise Exception("unknown field in MPEServiceMetadata")
        self.m[f] = v

    def set_fixed_price_in_cogs(self, group_name, price):
        if type(price) != int:
            raise Exception("Price should have int type")

        if not self.is_group_name_exists(group_name):
            raise Exception("the group %s is not present" % str(group_name))

        for group in self.m["groups"]:
            if group["group_name"] == group_name:
                is_fixed_price_enabled = False
                # default=True  it will change when we will go live with method level pricing
                if "pricing" in group:
                    for pricing in group['pricing']:
                        if pricing["price_model"] == "fixed_price":
                            is_fixed_price_enabled = True
                            pricing["price_in_cogs"] = price
                    if not is_fixed_price_enabled:
                        group["pricing"].append({"price_model": "fixed_price",
                                                 "price_in_cogs": price, "default": True})
                else:
                    group["pricing"] = [{"price_model": "fixed_price",
                                         "price_in_cogs": price, "default": True}]

    def set_method_price_in_cogs(self, group_name, package_name, service_name, method, price):
        if type(price) != int:
            raise Exception("Price should have int type")

        if not self.is_group_name_exists(group_name):
            raise Exception("the group %s is not present" % str(group_name))

        groups = self.m["groups"]
        for group in groups:
            if group["group_name"] == group_name:

                service_name = service_name
                package_name = package_name
                method_pricing = {"method_name": method,
                                  "price_in_cogs": price}
                pricings = []

                if 'pricings' in group:
                    pricings = group["pricings"]

                fixed_price_method_model_exist = False
                for pricing in pricings:
                    if pricing['price_model'] == 'fixed_price_per_method':
                        fixed_price_method_model_exist = True

                        if 'details' in pricing:
                            fixed_price_method_pricing_for_service_exist = False
                            for detail in pricing['details']:

                                if detail['service_name'] == service_name:
                                    # adding new method pricing for existing service
                                    fixed_price_method_pricing_for_service_exist = True
                                    detail['method_pricing'].append(
                                        method_pricing)

                            if not fixed_price_method_pricing_for_service_exist:
                                # pricing for new method for new service
                                pricing['details'].append({"service_name": service_name,
                                                           "method_pricing": [method_pricing]})
                        else:
                            pricing['details'] = [{"service_name": service_name,
                                                   "method_pricing": [method_pricing]}]

                if not fixed_price_method_model_exist:
                    fixed_price_per_method = {"package_name": package_name,
                                              "price_model": "fixed_price_per_method",
                                              "details": [
                                                  {"service_name": service_name, "method_pricing": [method_pricing]}]}
                    group['pricings'] = [fixed_price_per_method]

    def add_group(self, group_name):
        """ Return new group_id in base64 """
        if self.is_group_name_exists(group_name):
            raise Exception("the group \"%s\" is already present" %
                            str(group_name))

        self.m["groups"] += [{"group_name": group_name}]

    def remove_group(self, group_name):
        for group in self.m["groups"]:
            if group["group_name"] == group_name:
                self.m["groups"].remove(group)

    def get_tags(self):
        tags = []
        if "tags" in self.m:
            tags = self.m["tags"]
        return tags

    def add_tag(self, tag_name):
        if not "tags" in self.m:
            self.m["tags"] = []

        if tag_name in self.m["tags"]:
            print(f"The tag {str(tag_name)} is already present")
            return
        self.m["tags"] += [tag_name]

    def remove_tag(self, tag_name):
        if not "tags" in self.m:
            self.m["tags"] = []

        if tag_name not in self.m["tags"]:
            print(f"The tag {str(tag_name)} is not found")
            return
        self.m["tags"].remove(tag_name)

    def add_asset(self, asset_ipfs_hash, asset_type):
        # Check if we need to validation if same asset type is added twice if we need to add it or replace the existing one

        if 'assets' not in self.m:
            self.m['assets'] = {}

        # hero image will contain the single value
        if AssetType.is_single_value(asset_type):
            self.m['assets'][asset_type] = asset_ipfs_hash

        # images can contain multiple value
        elif asset_type == AssetType.IMAGES.value:
            if asset_type in self.m['assets']:
                self.m['assets'][asset_type].append(asset_ipfs_hash)
            else:
                self.m['assets'][asset_type] = [asset_ipfs_hash]
        else:
            raise Exception("Invalid asset type %s" % asset_type)

    def remove_all_assets(self):
        self.m['assets'] = {}

    def remove_assets(self, asset_type):
        if 'assets' in self.m:
            if AssetType.is_single_value(asset_type):
                self.m['assets'][asset_type] = ""
            elif asset_type == AssetType.IMAGES.value:
                self.m['assets'][asset_type] = []
            else:
                raise Exception("Invalid asset type %s" % asset_type)

    def add_endpoint_to_group(self, group_name, endpoint):
        if re.match("^\w+://", endpoint) is None:
            # TODO: Default to https when our tutorials show setting up a ssl certificate as well
            endpoint = 'http://' + endpoint
        if not is_valid_endpoint(endpoint):
            raise Exception("Endpoint is not a valid URL")
        if not self.is_group_name_exists(group_name):
            raise Exception("the group %s is not present" % str(group_name))
        if endpoint in self.get_all_endpoints_for_group(group_name):
            raise Exception("the endpoint %s is already present" %
                            str(endpoint))

        groups = self.m["groups"]
        for group in groups:
            if group["group_name"] == group_name:
                if 'endpoints' in group:
                    group['endpoints'].append(endpoint)
                else:
                    group['endpoints'] = [endpoint]

    def remove_all_endpoints_for_group(self, group_name):
        if not self.is_group_name_exists(group_name):
            raise Exception("Group name does not exist %s", group_name)

        groups = self.m["groups"]
        for group in groups:
            if group["group_name"] == group_name:
                group["endpoints"] = []

    def is_group_name_exists(self, group_name):
        """ check if group with given name is already exists """
        groups = self.m["groups"]
        for g in groups:
            if g["group_name"] == group_name:
                return True
        return False

    def get_group_by_group_id(self, group_id):
        """ return group with given group_id (return None if doesn't exists) """
        group_id_base64 = base64.b64encode(group_id).decode('ascii')
        groups = self.m["groups"]
        for g in groups:
            if g["group_id"] == group_id_base64:
                return g
        return None

    def set_free_calls_for_group(self, group_name, free_calls):
        groups = self.m["groups"]
        for g in groups:
            if g["group_name"] == group_name:
                g["free_calls"] = free_calls

    def set_freecall_signer_address(self, group_name, signer_address):
        groups = self.m["groups"]
        for g in groups:
            if g["group_name"] == group_name:
                g["free_call_signer_address"] = signer_address

    def get_json(self):
        return json.dumps(self.m)

    def get_json_pretty(self):
        return json.dumps(self.m, indent=4)

    def set_from_json(self, j):
        # TODO: we probaly should check the  consistensy of loaded json here
        #       check that it contains required fields
        self.m = json.loads(j)
        if not "tags" in self.m:
            self.m["tags"] = []

    def load(self, file_name):
        with open(file_name) as f:
            self.set_from_json(f.read())

    def save_pretty(self, file_name):
        with open(file_name, 'w') as f:
            f.write(self.get_json_pretty())

    def __getitem__(self, key):
        return self.m[key]

    def get(self, key, default=None):
        return self.m.get(key, default)

    def __contains__(self, key):
        return key in self.m

    def get_group_name_nonetrick(self, group_name=None):
        """ In all getter function in case of single payment group, group_name can be None """
        groups = self.m["groups"]
        if len(groups) == 0:
            raise Exception("Cannot find any groups in metadata")
        if not group_name:
            if len(groups) > 1:
                raise Exception(
                    "We have more than one payment group in metadata, so group_name should be specified")
            return groups[0]["group_name"]
        return group_name

    def get_group(self, group_name=None):
        group_name = self.get_group_name_nonetrick(group_name)
        for g in self.m["groups"]:
            if g["group_name"] == group_name:
                return g
        raise Exception('Cannot find group "%s" in metadata' % group_name)

    def get_group_id_base64(self, group_name=None):
        return self.get_group(group_name)["group_id"]

    def get_group_id(self, group_name=None):
        return base64.b64decode(self.get_group_id_base64(group_name))

    def get_payment_address(self, group_name=None):
        return self.get_group(group_name)["payment_address"]

    def add_daemon_address_to_group(self, group_name, daemon_address):
        groups = self.m["groups"]
        if not self.is_group_name_exists(group_name):
            raise Exception('Cannot find group "%s" in metadata' % group_name)
        for group in groups:
            if group["group_name"] == group_name:
                if 'daemon_addresses' in group:
                    group['daemon_addresses'].append(daemon_address)
                else:
                    group['daemon_addresses'] = [daemon_address]

    def remove_all_daemon_addresses_for_group(self, group_name):
        groups = self.m["groups"]
        if not self.is_group_name_exists(group_name):
            raise Exception('Cannot find group "%s" in metadata' % group_name)
        for group in groups:
            if group["group_name"] == group_name:
                group["daemon_addresses"] = []

    def get_all_endpoints_for_group(self, group_name):
        for group in self.m["groups"]:
            if group["group_name"] == group_name:
                if "endpoints" in group:
                    return group["endpoints"]
                return []

    def get_all_group_endpoints(self):
        group_endpoints = {}
        for group in self.m["groups"]:
            if "endpoints" in group:
                group_endpoints[group["group_name"]] = group['endpoints']
        return group_endpoints

    def get_all_endpoints_with_group_name(self):
        endpts_with_grp = defaultdict(list)
        for e in self.m["endpoints"]:
            endpts_with_grp[e['group_name']].append(e['endpoint'])
        return endpts_with_grp

    def get_endpoints_for_group(self, group_name=None):
        group_name = self.get_group_name_nonetrick(group_name)
        return [e["endpoint"] for e in self.m["endpoints"] if e["group_name"] == group_name]

    def add_contributor(self, name, email_id):
        if "contributors" in self.m:
            contributors = self.m["contributors"]
        else:
            contributors = []

        contributors.append(
            {
                "name": name,
                "email_id": email_id
            }
        )
        self.m["contributors"] = contributors

    def remove_contributor_by_email(self, email_id):
        self.m["contributors"] = [
            contributor for contributor in self.m["contributors"] if contributor["email_id"] != email_id]

    def group_init(self, group_name):
        """Required values for creating a new payment group.

        Args:
            group_name: If org contains only 1 payment group -> default_group, ask user for other groups otherwise.

        Raises:
            ValueError: User enters non-integer value for `fixed_price.`
            Exception: User enters same endpoints.
        """
        self.add_group(group_name)
        while True:
            try:
                fixed_price = int(input("Set fixed price: "))
            except ValueError:
                print("Enter a valid integer.")
            else:
                self.set_fixed_price_in_cogs(group_name, fixed_price)
                break
        while True:
            try:
                endpoints = input("Add endpoints as comma separated values: ").split(',')
                if endpoints[0] == "":
                    print("Endpoints required.")
                else:
                    for endpoint in endpoints:
                        self.add_endpoint_to_group(group_name, endpoint.strip())
                    break
            except Exception as e:
                print(e)
        while True:
            daemon_addresses = input("Add daemon addresses as comma separated values: ").split(',')
            if daemon_addresses[0] == "":
                print("Daemon address required.")
            else:
                for daemon_address in daemon_addresses:
                    self.add_daemon_address_to_group(group_name, daemon_address.strip())
                break
        if input('Free calls included? [y/n] ').lower() == 'y':
            self.set_free_calls_for_group(group_name, int(input('free calls: (15) ') or 15))
            self.set_freecall_signer_address(group_name, input('free call signer address: '))

    def add_media(self, url, media_type, hero_img=False):
        """Add new individual media to service metadata."""
        if 'media' not in self.m:
            self.m['media'] = []
        individual_media = {}
        if hero_img:
            assert (media_type == 'image'), f"{media_type.upper()} media-type cannot be a hero-image."
            assert (not self._is_asset_type_exists()), "Hero-image already exists (only 1 unique hero-image allowed.)"
            individual_media['asset_type'] = AssetType.HERO_IMAGE.value  # Dependency with AssetType, fix if obsolete
        if len(self.m['media']) == 0:
            individual_media['order'] = 1
        else:
            individual_media['order'] = self.m['media'][-1]['order'] + 1
        individual_media['url'] = url
        individual_media['file_type'] = media_type
        if media_type == 'image':
            individual_media['alt_text'] = 'hover_on_the_image_text'
        else:
            individual_media['alt_text'] = 'hover_on_the_video_url'
        self.m['media'].append(individual_media)

    def remove_media(self, order):
        """Remove individual media from service metadata using unique order key."""
        assert (len(self.m['media']) > 0), "No media content to remove."
        assert (order > 0), "Order of individual media starts from 1."
        del_position = -1
        for i in range(len(self.m['media'])):
            if order == self.m['media'][i]['order']:
                del self.m['media'][i]
                del_position = i
                break
        if del_position == -1:
            raise Exception(f"Media with order: {order} not found.")
        for i in range(del_position, len(self.m['media'])):
            self.m['media'][i]['order'] -= 1

    def remove_all_media(self):
        """Remove all individual media from metadata."""
        self.m['media'].clear()

    def swap_media_order(self, move_from, move_to):
        """Swap orders of two different media given their individual orders (move_from, move_to)."""
        assert (len(self.m['media']) + 1 > move_from > 0), f"Order {move_from} out of bounds."
        assert (len(self.m['media']) + 1 > move_to > 0), f"Order {move_to} out of bounds."
        self.m['media'][move_to - 1], self.m['media'][move_from - 1] = self.m['media'][move_from - 1], self.m['media'][
            move_to - 1]
        self.m['media'][move_to - 1]['order'], self.m['media'][move_from - 1]['order'] = self.m['media'][move_from - 1][
            'order'], \
            self.m['media'][move_to - 1][
                'order']

    def change_media_order(self):
        """Mini REPL to change order of all individual media"""
        order_range = range(1, len(self.m['media']) + 1)
        available_orders = list(order_range)
        for individual_media in self.m['media']:
            print(f"File Type: {individual_media['file_type']}, Current Order: {individual_media['order']}")
            while True:
                try:
                    new_order = int(input(f"Enter new order for {individual_media['url']}: "))
                except ValueError:
                    print("Error: Order entered not a number. Try again.")
                else:
                    if new_order in available_orders:
                        individual_media['order'] = new_order
                        available_orders.remove(new_order)
                        break
                    elif new_order not in order_range:
                        print(
                            f"Media array contains only {len(self.m['media'])} items. Enter order between [{order_range.start}, {order_range.stop - 1}]")
                    else:
                        print(f"Order already taken. Available orders: {available_orders}")
        self.m['media'].sort(key=lambda x: x['order'])

    def _is_asset_type_exists(self):
        """Return boolean on whether asset type already exists"""
        media = self.m['media']
        for individual_media in media:
            if 'asset_type' in individual_media:
                return True
        return False

    def add_description(self):
        if 'service_description' not in self.m:
            self.m['service_description'] = {
                "url": input("user guide url: "),
                "long_description": input("service long description: "),
                "short_description": input("service short description: ")
            }


def load_mpe_service_metadata(f):
    metadata = MPEServiceMetadata()
    metadata.load(f)
    return metadata


def mpe_service_metadata_from_json(j):
    metadata = MPEServiceMetadata()
    metadata.set_from_json(j)
    return metadata
