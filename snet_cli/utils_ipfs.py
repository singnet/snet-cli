# utils related to ipfs
import tarfile
import base58
import glob
import io
import os


# make tar from protodir/*proto, and publish this tar in ipfs
# return base58 encoded ipfs hash
def publish_proto_in_ipfs(ipfs_client, protodir):
    files = glob.glob(os.path.join(protodir, "*.proto"))
    
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
def get_from_ipfs_and_checkhash(self, ipfs_client, ipfs_hash_base58):
    data  = ipfs_client.cat(ipfs_hash_base58)
    print("!!! We must check that hash in IPFS is correct (we cannot be sure that ipfs is not compromized) !!! Please implement it !!!")
    return data
