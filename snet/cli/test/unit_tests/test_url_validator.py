import unittest

from snet.cli.utils.utils import is_valid_url


class TestURLValidator(unittest.TestCase):
    
    def test_valid_urls(self):
        valid_urls = [
            "https://www.example.com",
            "http://example.com",
            "ftp://ftp.example.com",
            "https://localhost",
            "http://127.0.0.1",
            "https://[::1]",
            "https://www.example.com",
            "http://localhost:5432",
            "https://192.168.20.20",
            "https://192.168.20.20:8000",
            "https://192.168.20.20:8001/get_objects",
            "http://0.0.0.0:8000"
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(is_valid_url(url))
    
    def test_invalid_urls(self):
        invalid_urls = [
            "www.example.com",
            "http//example.com",
            "://missing.scheme.com",
            "http://",
            "http://invalid_domain",
            "ftp://-invalid.com",
            "http://http://example.com"
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(is_valid_url(url))


if __name__ == '__main__':
    unittest.main()
