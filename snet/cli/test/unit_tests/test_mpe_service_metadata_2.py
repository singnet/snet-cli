"""Unit test cases for the media query commands in snet-cli.

This module contains the unit test cases for media methods of the MPEServiceMetadata class,
mainly add_media, remove_media, remove_all_media, swap_media_order, and change_media_order.
"""
import unittest
from unittest.mock import patch

from snet.snet_cli.metadata.service import MPEServiceMetadata


class TestMediaMethods(unittest.TestCase):
    def setUp(self):
        """Runs before every unit test case.

        Mock fixtures are created as they are used multiple times in each test case. Ensure consistent format:
            {
                "asset_type": String,
                "order": Integer,
                "url": String,
                "file_type": String,
                "alt_text": String
            }

        Other common checks during start of test case:
            1) `media` present in metadata.
            2) `media` should be of type list.
            3) `media` should be empty.
        """
        self.metadata = MPEServiceMetadata()
        self.mock_fixture_1 = dict(order=1,
                                   asset_type="hero_image",
                                   url="www.example1.com",
                                   file_type="image",
                                   alt_text="hover_on_the_image_text")
        self.mock_fixture_2 = dict(order=2,
                                   url="www.example2.com",
                                   file_type="video",
                                   alt_text="hover_on_the_video_url")
        self.assertIn('media', self.metadata.m, msg="`media` not initialized in metadata")
        self.assertIsInstance(self.metadata.m['media'], list, msg="`media` in metadata should be a list")
        self.assertListEqual(self.metadata.m['media'], [], msg="Media array should be empty during initialization")

    def test_add_media(self):
        self.metadata.add_media('www.example1.com', 'image', True)
        self.assertEqual(self.metadata.m['media'][0], self.mock_fixture_1, msg="Media addition unsuccessful")
        with self.assertRaises(AssertionError, msg="Multiple hero images constraint not handled"):
            self.metadata.add_media('www.example2.com', 'image', True)
        self.metadata.add_media('www.example2.com', 'video', False)
        self.assertEqual(self.metadata.m['media'][1], self.mock_fixture_2,
                         msg='Probable issue with Order ID sequencing')

    def test_remove_media(self):
        with self.assertRaises(AssertionError, msg="Media removal from empty list not handled"):
            self.metadata.remove_media(1)
        with self.assertRaises(AssertionError, msg="Out of bounds Order ID not handled"):
            self.metadata.remove_media(-1)
        self.metadata.add_media('www.example2.com', 'video', hero_img=False)
        self.metadata.add_media('www.example1.com', 'image', hero_img=True)
        with self.assertRaises(Exception, msg="Non-existent Order ID not handled"):
            self.metadata.remove_media(100)
        self.metadata.remove_media(1)
        self.assertDictEqual(self.metadata.m['media'][0], self.mock_fixture_1,
                             msg="Order ID sequencing after individual media deletion not handled")
        self.metadata.remove_media(1)
        self.assertListEqual(self.metadata.m['media'], [], msg="Individual media removal not handled")

    def test_remove_all_media(self):
        for _ in range(5):
            self.metadata.m['media'].append(self.mock_fixture_1)
        self.metadata.remove_all_media()
        self.assertListEqual(self.metadata['media'], [], msg="Issue with removal of all individual media")

    def test_swap_media_order(self):
        self.metadata.add_media('www.example2.com', 'video', hero_img=False)
        self.metadata.add_media('www.example1.com', 'image', hero_img=True)
        with self.assertRaises(AssertionError, msg="Order supposed to be out of bounds"):
            self.metadata.swap_media_order(1, 3)
            self.metadata.swap_media_order(3, 1)
        self.metadata.swap_media_order(1, 2)
        self.assertSequenceEqual(self.metadata.m['media'], [self.mock_fixture_1, self.mock_fixture_2],
                                 msg="Issue with media swapping", seq_type=list)

    def test_change_media_order(self):
        """Tests the REPL for changing multiple individual media order.

        Mock inputs through side effects are passed to the input stream using `builtins.input`,
        and StopIteration assertion should be raised for incorrect inputs.

        Context Manager is used to limit the scope of the patch to test different side effects.
        Read more at https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.side_effect
        """
        self.metadata.add_media('www.example2.com', 'video', hero_img=False)
        self.metadata.add_media('www.example1.com', 'image', hero_img=True)
        with patch('builtins.input', side_effect=['3', '1']):
            self.assertRaises(StopIteration, self.metadata.change_media_order)
        with patch('builtins.input', side_effect=['1', '3']):
            self.assertRaises(StopIteration, self.metadata.change_media_order)
        with patch('builtins.input', side_effect=['2', '1']):
            self.metadata.change_media_order()
            self.assertSequenceEqual(self.metadata.m['media'], [self.mock_fixture_1, self.mock_fixture_2],
                                     msg="Issue with media swapping", seq_type=list)


if __name__ == '__main__':
    unittest.main()
