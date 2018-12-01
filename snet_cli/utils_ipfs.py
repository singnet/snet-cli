# utils related to ipfs
import tarfile
import glob
import io
import os


# make tar from protodir/*proto, and publish this tar in ipfs
# return base58 encoded ipfs hash
def publish_proto_in_ipfs(ipfs_client, protodir):
    
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

# get file from ipfs
# We must check the hash becasue we cannot believe that ipfs_client wasn't been compromise
def get_from_ipfs_and_checkhash(ipfs_client, ipfs_hash_base58):
    data  = ipfs_client.cat(ipfs_hash_base58)
    print("!!! We must check that hash in IPFS is correct (we cannot be sure that ipfs is not compromized) !!! Please implement it !!!")
    return data

# Convert in and from bytes uri format used in Registry contract
# TODO: we should pad string with zeros till closest 32 bytes word because of a bug in processReceipt (in snet_cli.contract.process_receipt)
def hash_to_bytesuri(s):
    s = "ipfs://" + s
    return s.encode("ascii").ljust(32 * (len(s)//32 + 1), b"\0")

def bytesuri_to_hash(s):
    s = s.rstrip(b"\0").decode('ascii')
    if (not s.startswith("ipfs://")):
        raise Exception("We support only ipfs uri in Registry")
    return s[7:]
