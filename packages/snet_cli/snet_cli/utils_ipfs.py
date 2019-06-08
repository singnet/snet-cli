""" Utilities related to ipfs """
import tarfile
import glob
import io
import os

import base58
import multihash

def publish_proto_in_ipfs(ipfs_client, protodir):
    """
    make tar from protodir/*proto, and publish this tar in ipfs
    return base58 encoded ipfs hash
    """
    
    if (not os.path.isdir(protodir)):
        raise Exception("Directory %s doesn't exists"%protodir)

    files = glob.glob(os.path.join(protodir, "*.proto"))

    if (len(files) == 0):
        raise Exception("Cannot find any %s files"%(os.path.join(protodir, "*.proto")) )

    # We are sorting files before we add them to the .tar since an archive containing the same files in a different
    # order will produce a different content hash;
    files.sort()
        
    tarbytes  = io.BytesIO()        
    tar       = tarfile.open(fileobj=tarbytes, mode="w")
    for f in files:
        tar.add(f, os.path.basename(f))
    tar.close()
    return ipfs_client.add_bytes(tarbytes.getvalue())

def get_from_ipfs_and_checkhash(ipfs_client, ipfs_hash_base58, validate=True):
    """
    Get file from ipfs
    We must check the hash becasue we cannot believe that ipfs_client wasn't been compromise
    """
    if validate:
        from snet.snet_cli.resources.proto.unixfs_pb2 import Data
        from snet.snet_cli.resources.proto.merckledag_pb2 import MerkleNode

        # No nice Python library to parse ipfs blocks, so do it ourselves.
        block_data = ipfs_client.block_get(ipfs_hash_base58)
        mn = MerkleNode()
        mn.ParseFromString(block_data)
        unixfs_data = Data()
        unixfs_data.ParseFromString(mn.Data)
        assert unixfs_data.Type == unixfs_data.DataType.Value('File'), "IPFS hash must be a file"
        data = unixfs_data.Data
        
        # multihash has a badly registered base58 codec, overwrite it...
        multihash.CodecReg.register('base58', base58.b58encode, base58.b58decode)
        # create a multihash object from our ipfs hash
        mh = multihash.decode(ipfs_hash_base58.encode('ascii'), 'base58')
        
        # Convenience method lets us directly use a multihash to verify data
        if not mh.verify(block_data):
            raise Exception("IPFS hash mismatch with data")
    else:
        data = ipfs_client.cat(ipfs_hash_base58)
    return data

def hash_to_bytesuri(s):
    """
    Convert in and from bytes uri format used in Registry contract
    """
    # TODO: we should pad string with zeros till closest 32 bytes word because of a bug in processReceipt (in snet_cli.contract.process_receipt)
    s = "ipfs://" + s
    return s.encode("ascii").ljust(32 * (len(s)//32 + 1), b"\0")

def bytesuri_to_hash(s):
    s = s.rstrip(b"\0").decode('ascii')
    if (not s.startswith("ipfs://")):
        raise Exception("We support only ipfs uri in Registry")
    return s[7:]

def safe_extract_proto_from_ipfs(ipfs_client, ipfs_hash, protodir):
    """
    Tar files might be dangerous (see https://bugs.python.org/issue21109,
    and https://docs.python.org/3/library/tarfile.html, TarFile.extractall warning)
    we extract only simple files
    """
    spec_tar = get_from_ipfs_and_checkhash(ipfs_client, ipfs_hash)
    with tarfile.open(fileobj=io.BytesIO(spec_tar)) as f:
        for m in f.getmembers():
            if (os.path.dirname(m.name) != ""):
                raise Exception("tarball has directories. We do not support it.")
            if (not m.isfile()):
                raise Exception("tarball contains %s which is not a files"%m.name)
            fullname = os.path.join(protodir, m.name)
            if (os.path.exists(fullname)):
                raise Exception("%s already exists."%fullname)
        # now it is safe to call extractall
        f.extractall(protodir)
