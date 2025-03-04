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


def publish_file_in_filecoin(filecoin_client, filepath):
    """
    Push a file to Filecoin given its path.
    """
    try:
        response = filecoin_client.upload(filepath)
        return response['data']['Hash']
    except Exception as err:
        print("File upload error: ", err)


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
    tar = tarfile.open(fileobj=tarbytes, mode="w:gz")
    for f in files:
        tar.add(f, os.path.basename(f))
    tar.close()
    return ipfs_client.add_bytes(tarbytes.getvalue())


def publish_proto_in_filecoin(filecoin_client, protodir):
    """
    Create a tar archive from protodir/*.proto, and publish this tar archive to Lighthouse.
    Return the hash (CID) of the uploaded archive.
    """

    if not os.path.isdir(protodir):
        raise Exception("Directory %s doesn't exist" % protodir)

    files = glob.glob(os.path.join(protodir, "*.proto"))

    if len(files) == 0:
        raise Exception("Cannot find any .proto files in %s" % protodir)

    files.sort()

    tarbytes = io.BytesIO()

    with tarfile.open(fileobj=tarbytes, mode="w:gz") as tar:
        for f in files:
            tar.add(f, os.path.basename(f))
    tarbytes.seek(0)

    temp_tar_path = os.path.join(protodir, "proto_files.tar")
    with open(temp_tar_path, 'wb') as temp_tar_file:
        temp_tar_file.write(tarbytes.getvalue())
    response = filecoin_client.upload(source=temp_tar_path, tag="")

    os.remove(temp_tar_path)

    return response['data']['Hash']


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


def hash_to_bytesuri(s, storage_type="ipfs", to_encode=True):
    """
    Convert in and from bytes uri format used in Registry contract
    """
    # TODO: we should pad string with zeros till closest 32 bytes word because of a bug in processReceipt (in snet_cli.contract.process_receipt)
    if storage_type == "ipfs":
        s = "ipfs://" + s
    elif storage_type == "filecoin":
        s = "filecoin://" + s

    if to_encode:
        return s.encode("ascii").ljust(32 * (len(s)//32 + 1), b"\0")
    else:
        return s # for 'service_api_source' metadata field
