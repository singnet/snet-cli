""" Utilities related to ipfs """
import tarfile
import glob
import io
import os

import base58
import multihash


def publish_file_in_ipfs(ipfs_client, filepath, wrap_with_directory=True):
    """
        push a file to ipfs given its path
    """
    try:
        with open(filepath, 'r+b') as file:
            result = ipfs_client.add(
                file, pin=True, wrap_with_directory=wrap_with_directory)
            if wrap_with_directory:
                return result[1]['Hash']+'/'+result[0]['Name']
            return result['Hash']
    except Exception as err:
        print("File error ", err)


def publish_proto_in_ipfs(ipfs_client, protodir):
    """
    make tar from protodir/*proto, and publish this tar in ipfs
    return base58 encoded ipfs hash
    """

    if not os.path.isdir(protodir):
        raise Exception("Directory %s doesn't exists" % protodir)

    files = glob.glob(os.path.join(protodir, "*.proto"))

    if len(files) == 0:
        raise Exception("Cannot find any %s files" %
                        (os.path.join(protodir, "*.proto")))

    # We are sorting files before we add them to the .tar since an archive containing the same files in a different
    # order will produce a different content hash;
    files.sort()

    tarbytes = io.BytesIO()
    tar = tarfile.open(fileobj=tarbytes, mode="w")
    for f in files:
        tar.add(f, os.path.basename(f))
    tar.close()
    return ipfs_client.add_bytes(tarbytes.getvalue())


def get_from_ipfs_and_checkhash(ipfs_client, ipfs_hash_base58, validate=True):
    """
    Get file from IPFS. If validate is True, verify the integrity of the file using its hash.
    """

    data = ipfs_client.cat(ipfs_hash_base58)

    if validate:
        block_data = ipfs_client.block.get(ipfs_hash_base58)

        # print(f"IPFS hash (Base58): {ipfs_hash_base58}")
        # print(f"Block data length: {len(block_data)}")

        # Decode Base58 bash to multihash
        try:
            mh = multihash.decode(ipfs_hash_base58.encode('ascii'), "base58")
        except Exception as e:
            raise ValueError(f"Invalid multihash for IPFS hash: {ipfs_hash_base58}. Error: {str(e)}") from e

        if not mh.verify(block_data):  # Correctly using mh instance for verification
            raise Exception("IPFS hash mismatch with data")

    return data


def hash_to_bytesuri(s):
    """
    Convert in and from bytes uri format used in Registry contract
    """
    # TODO: we should pad string with zeros till closest 32 bytes word because of a bug in processReceipt (in snet_cli.contract.process_receipt)
    s = "ipfs://" + s
    return s.encode("ascii").ljust(32 * (len(s)//32 + 1), b"\0")
