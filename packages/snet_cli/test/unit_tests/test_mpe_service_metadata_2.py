import unittest
from snet.snet_cli.metadata.service import MPEServiceMetadata


class TestMediaMethods(unittest.TestCase):
    def setUp(self):
        self.metadata = MPEServiceMetadata()
        self.mock_data = dict(asset_type='hero_image',
                              order=1,
                              file_type='image',
                              url='www.example.com',
                              alt_text='hover_on_the_image_text')

    def test_add_media(self):
        self.metadata.add_media('www.example.com', 'image', True)
        self.assertEqual(self.metadata['media'][0], self.mock_data)
        self.assertRaises(AssertionError, self.metadata.add_media, 'www.example.com', 'image', True)
        self.assertRaises(AssertionError, self.metadata.add_media, 'www.example.com', 'video', True)

    def test_remove_media(self):
        self.assertRaises(AssertionError, self.metadata.remove_media, 1)
        self.assertRaises(AssertionError, self.metadata.remove_media, -1)
        self.metadata['media'].append(self.mock_data)
        self.assertRaises(Exception, self.metadata.remove_media, 2)
        self.assertIsNone(self.metadata.remove_media(1))
        self.assertRaises(AssertionError, self.metadata.remove_media, 1)


if __name__ == '__main__':
    unittest.main()
