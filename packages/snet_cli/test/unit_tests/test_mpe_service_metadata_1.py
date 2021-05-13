import unittest

from snet.snet_cli.metadata.service import MPEServiceMetadata

class TestStringMethods(unittest.TestCase):
    
    def test_init(self):
        metadata = MPEServiceMetadata()
        ipfs_hash = "Qmb6ZkZrVUU6A2VW3PDsrRVT7etPnAD24bv3jr7MwQCWQG"
        mpe_address = "0x592E3C0f3B038A0D673F19a18a773F993d4b2610"
        display_name = "Display Name"
        encoding  = "grpc"
        service_type = "grpc"
        payment_expiration_threshold = 31415
        metadata.set_simple_field("model_ipfs_hash",              ipfs_hash)
        metadata.set_simple_field("mpe_address",                  mpe_address)
        metadata.set_simple_field("display_name",                 display_name)
        metadata.set_simple_field("encoding",                     encoding)
        metadata.set_simple_field("service_type",                 service_type)
        metadata.set_simple_field("payment_expiration_threshold", payment_expiration_threshold)
                                                        
        self.assertEqual(metadata["model_ipfs_hash"], ipfs_hash)
        self.assertEqual(metadata["mpe_address"],     mpe_address)
        self.assertEqual(metadata["display_name"],    display_name)
        self.assertEqual(metadata["encoding"],        encoding)
        self.assertEqual(metadata["service_type"],    service_type)
        self.assertEqual(metadata["payment_expiration_threshold"],   payment_expiration_threshold)

if __name__ == '__main__':
    unittest.main()

